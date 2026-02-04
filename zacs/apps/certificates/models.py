from django.db import models
from django.conf import settings
from django.core.signing import Signer
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
import datetime
import base64
import hashlib


def _get_fernet():
    """用SECRET_KEY派生Fernet密钥"""
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


class CertificateAuthority(models.Model):
    """证书颁发机构"""
    name = models.CharField(max_length=255, unique=True, verbose_name="CA名称")
    _private_key = models.TextField(db_column='private_key', verbose_name="私钥(加密)")
    certificate = models.TextField(verbose_name="CA证书(PEM)")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "证书颁发机构"
        verbose_name_plural = "证书颁发机构"
        db_table = "certificate_authority"

    @property
    def private_key(self):
        """解密私钥"""
        if not self._private_key:
            return None
        try:
            return _get_fernet().decrypt(self._private_key.encode()).decode()
        except:
            # 兼容旧数据（未加密的）
            return self._private_key

    @private_key.setter
    def private_key(self, value):
        """加密存储私钥"""
        if value:
            self._private_key = _get_fernet().encrypt(value.encode()).decode()
        else:
            self._private_key = ''

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
    """服务器证书"""
    hostname = models.CharField(max_length=255, unique=True, verbose_name="主机名")
    ca = models.ForeignKey(CertificateAuthority, on_delete=models.CASCADE)
    _private_key = models.TextField(db_column='private_key', verbose_name="私钥(加密)")
    certificate = models.TextField(verbose_name="证书(PEM)")
    pfx_data = models.TextField(verbose_name="PFX(Base64)")
    thumbprint = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_revoked = models.BooleanField(default=False)
    revocation_reason = models.CharField(max_length=255, blank=True, null=True)
    revocation_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "服务器证书"
        verbose_name_plural = "服务器证书"
        db_table = "server_certificate"

    @property
    def private_key(self):
        if not self._private_key:
            return None
        try:
            return _get_fernet().decrypt(self._private_key.encode()).decode()
        except:
            return self._private_key

    @private_key.setter
    def private_key(self, value):
        if value:
            self._private_key = _get_fernet().encrypt(value.encode()).decode()
        else:
            self._private_key = ''

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
    """客户端证书"""
    name = models.CharField(max_length=255)
    ca = models.ForeignKey(CertificateAuthority, on_delete=models.CASCADE)
    _private_key = models.TextField(db_column='private_key', verbose_name="私钥(加密)")
    certificate = models.TextField(verbose_name="证书(PEM)")
    thumbprint = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    assigned_to_user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "客户端证书"
        verbose_name_plural = "客户端证书"
        db_table = "client_certificate"

    @property
    def private_key(self):
        if not self._private_key:
            return None
        try:
            return _get_fernet().decrypt(self._private_key.encode()).decode()
        except:
            return self._private_key

    @private_key.setter
    def private_key(self, value):
        if value:
            self._private_key = _get_fernet().encrypt(value.encode()).decode()
        else:
            self._private_key = ''

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