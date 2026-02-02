from django.db import models
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.core.exceptions import ValidationError
import datetime
import base64
import os


class CertificateAuthority(models.Model):
    """证书颁发机构模型"""
    name = models.CharField(max_length=255, unique=True, verbose_name="CA名称")
    private_key = models.TextField(verbose_name="私钥(加密存储)")  # 加密存储
    certificate = models.TextField(verbose_name="CA证书(PEM格式)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    expires_at = models.DateTimeField(verbose_name="过期时间", null=True, blank=True)  # 允许为空
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    description = models.TextField(blank=True, null=True, verbose_name="描述")

    class Meta:
        verbose_name = "证书颁发机构"
        verbose_name_plural = "证书颁发机构"
        db_table = "certificate_authority"

    def generate_self_signed_cert(self):
        """生成自签名CA证书"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096  # 使用更强的密钥长度
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ZASCA Corp"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Security Department"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.name),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=3650)  # 10年有效期
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                content_commitment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256())

        self.private_key = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        self.certificate = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
        self.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=3650)

    def __str__(self):
        return f"CA: {self.name}"


class ServerCertificate(models.Model):
    """服务器证书模型"""
    hostname = models.CharField(max_length=255, unique=True, verbose_name="主机名")
    ca = models.ForeignKey(CertificateAuthority, on_delete=models.CASCADE, verbose_name="所属CA")
    private_key = models.TextField(verbose_name="私钥(加密存储)")  # 加密存储
    certificate = models.TextField(verbose_name="服务器证书(PEM格式)")
    pfx_data = models.TextField(verbose_name="PFX数据(Base64编码)")  # Base64编码的PFX数据
    thumbprint = models.CharField(max_length=255, unique=True, verbose_name="证书指纹(SHA1)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    expires_at = models.DateTimeField(verbose_name="过期时间", null=True, blank=True)  # 允许为空
    is_revoked = models.BooleanField(default=False, verbose_name="是否已吊销")
    revocation_reason = models.CharField(max_length=255, blank=True, null=True, verbose_name="吊销原因")
    revocation_date = models.DateTimeField(blank=True, null=True, verbose_name="吊销时间")

    class Meta:
        verbose_name = "服务器证书"
        verbose_name_plural = "服务器证书"
        db_table = "server_certificate"

    def generate_server_cert(self, hostname, san_names=None):
        """为指定主机生成服务器证书"""
        if not san_names:
            san_names = []

        # 使用CA私钥签署服务器证书
        ca_cert = x509.load_pem_x509_certificate(self.ca.certificate.encode())
        ca_private_key = serialization.load_pem_private_key(
            self.ca.private_key.encode(), password=None
        )

        server_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])

        # 构建证书主体
        builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.issuer
        ).public_key(
            server_private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)  # 1年有效期
        ).add_extension(
            x509.KeyUsage(
                key_encipherment=True,
                digital_signature=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            ]),
            critical=True,
        )

        # 添加SAN扩展
        if san_names:
            san_list = [x509.DNSName(name) for name in san_names]
            san_list.append(x509.DNSName(hostname))
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )

        cert = builder.sign(ca_private_key, hashes.SHA256())

        self.private_key = server_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        self.certificate = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

        # 生成PFX格式证书（包含私钥）
        from cryptography.hazmat.primitives.serialization.pkcs12 import serialize_key_and_certificates
        pfx = serialize_key_and_certificates(
            name=hostname.encode(),
            key=server_private_key,
            cert=cert,
            cas=[ca_cert],
            encryption_algorithm=serialization.NoEncryption()  # 可以选择加密
        )

        self.pfx_data = base64.b64encode(pfx).decode('utf-8')

        # 计算证书指纹(SHA1)
        fingerprint = cert.fingerprint(hashes.SHA1())
        self.thumbprint = ":".join(f"{byte:02X}" for byte in fingerprint)

        self.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=365)

    def revoke(self, reason=""):
        """吊销证书"""
        self.is_revoked = True
        self.revocation_reason = reason
        self.revocation_date = datetime.datetime.utcnow()
        self.save()

    def __str__(self):
        return f"Server Cert: {self.hostname}"


class ClientCertificate(models.Model):
    """客户端证书模型，用于C端连接H端时的身份认证"""
    name = models.CharField(max_length=255, verbose_name="证书名称")
    ca = models.ForeignKey(CertificateAuthority, on_delete=models.CASCADE, verbose_name="所属CA")
    private_key = models.TextField(verbose_name="私钥(加密存储)")  # 加密存储
    certificate = models.TextField(verbose_name="客户端证书(PEM格式)")
    thumbprint = models.CharField(max_length=255, unique=True, verbose_name="证书指纹(SHA1)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    expires_at = models.DateTimeField(verbose_name="过期时间", null=True, blank=True)  # 允许为空
    assigned_to_user = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="分配给用户"
    )
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    description = models.TextField(blank=True, null=True, verbose_name="描述")

    class Meta:
        verbose_name = "客户端证书"
        verbose_name_plural = "客户端证书"
        db_table = "client_certificate"

    def generate_client_cert(self, name, user=None, description=""):
        """生成客户端证书"""
        # 使用CA私钥签署客户端证书
        ca_cert = x509.load_pem_x509_certificate(self.ca.certificate.encode())
        ca_private_key = serialization.load_pem_private_key(
            self.ca.private_key.encode(), password=None
        )

        client_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )

        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ZASCA Corp"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Control Center"),
        ])

        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.issuer
        ).public_key(
            client_private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)  # 1年有效期
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).sign(ca_private_key, hashes.SHA256())

        self.name = name
        self.private_key = client_private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')

        self.certificate = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')

        # 计算证书指纹(SHA1)
        fingerprint = cert.fingerprint(hashes.SHA1())
        self.thumbprint = ":".join(f"{byte:02X}" for byte in fingerprint)

        self.expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=365)
        self.assigned_to_user = user
        self.description = description

    def __str__(self):
        user_info = f" (User: {self.assigned_to_user.username})" if self.assigned_to_user else ""
        return f"Client Cert: {self.name}{user_info}"