"""
本地图形验证码工具类
使用Pillow生成和验证图形验证码
"""
import random
import string
import io
import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from django.core.cache import cache
from django.http import HttpResponse
from django.conf import settings
import os


# 设置日志
logger = logging.getLogger(__name__)


def generate_captcha_image(size=(120, 40), chars=None, count=4, color=True, noise=1, noise_color=True, font_size=25):
    """
    生成图形验证码图片
    
    Args:
        size: 图片尺寸 (宽, 高)
        chars: 验证码字符集合
        count: 验证码字符数
        color: 是否使用彩色
        noise: 干扰线数量
        noise_color: 干扰线是否彩色
        font_size: 字体大小
    
    Returns:
        tuple: (验证码文本, 图片二进制数据)
    """
    if chars is None:
        chars = string.ascii_letters + string.digits  # 包含大小写字母和数字
        # 排除容易混淆的字符
        chars = chars.replace('0', '').replace('O', '').replace('o', '').replace('l', '').replace('I', '').replace('i', '')
    
    # 随机生成验证码文本
    captcha_text = ''.join(random.choice(chars) for _ in range(count))
    
    # 创建图像
    width, height = size
    image = Image.new('RGB', (width, height), (255, 255, 255))
    
    # 创建绘图画布
    draw = ImageDraw.Draw(image)
    
    # 设置字体（尝试使用系统字体）
    try:
        # 尝试使用系统字体
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        try:
            # 尝试其他常见字体
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", font_size)  # macOS
        except IOError:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)  # Linux
            except IOError:
                # 如果找不到字体，使用默认字体
                font = ImageFont.load_default()
    
    # 生成随机颜色
    def get_random_color():
        return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    
    # 绘制干扰点
    for _ in range(width * height // 4):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=get_random_color())
    
    # 绘制干扰线
    for _ in range(noise):
        start = (random.randint(0, width), random.randint(0, height))
        end = (random.randint(0, width), random.randint(0, height))
        line_color = get_random_color() if noise_color else (random.randint(0, 150), random.randint(0, 150), random.randint(0, 150))
        draw.line([start, end], fill=line_color, width=1)
    
    # 计算文字位置，使其居中显示
    try:
        # For newer versions of Pillow
        bbox = draw.textbbox((0, 0), captcha_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # For older versions of Pillow
        text_width, text_height = draw.textsize(captcha_text, font=font)
    
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    
    # 绘制验证码文字
    for i, char in enumerate(captcha_text):
        # 每个字符可能有不同的颜色和轻微的位置偏移
        char_color = get_random_color() if color else (0, 0, 0)
        char_x = text_x + i * (text_width // count)
        
        # 添加轻微的角度偏移使字符看起来更自然
        char_image = Image.new('RGBA', (font_size, font_size * 2), (255, 255, 255, 0))
        char_draw = ImageDraw.Draw(char_image)
        char_draw.text((0, 0), char, font=font, fill=char_color)
        
        # 旋转字符增加复杂度
        angle = random.randint(-15, 15)
        char_image = char_image.rotate(angle, expand=0, fillcolor=(255, 255, 255, 0))
        
        # 将旋转后的字符粘贴到主图像上
        image.paste(char_image, (char_x, text_y), char_image)
    
    # 对图像应用模糊效果以增加难度
    image = image.filter(ImageFilter.SMOOTH)
    
    # 将图像转换为字节流
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    
    return captcha_text, buffer.getvalue()


def generate_captcha():
    """
    生成验证码，返回验证码文本和图片数据，并将验证码存储到缓存中
    
    Returns:
        dict: 包含验证码ID和图片数据的字典
    """
    captcha_text, image_data = generate_captcha_image()
    
    # 生成唯一的验证码ID
    captcha_id = 'captcha_' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # 将验证码文本存储到缓存中，设置过期时间为5分钟
    cache.set(captcha_id, captcha_text.lower(), 300)
    # 同时初始化尝试次数计数器
    cache.set(f"captcha_attempts_{captcha_id}", 0, 300)  # 5分钟内最多尝试
    
    logger.info(f"Generated captcha: ID={captcha_id}, text={captcha_text}")
    
    return {
        'captcha_id': captcha_id,
        'image_data': image_data
    }


def verify_captcha(captcha_id, user_input, consume=True, max_attempts=5, check_attempts=True):
    """
    验证用户输入的验证码是否正确
    
    Args:
        captcha_id: 验证码ID
        user_input: 用户输入的验证码
        consume: 是否在验证成功后删除验证码（默认为True）
        max_attempts: 最大尝试次数（默认为5次）
        check_attempts: 是否检查尝试次数（默认为True）

    Returns:
        bool: 验证是否成功
    """
    logger.debug(f"Verifying captcha: ID={captcha_id}, user_input={user_input}, consume={consume}, check_attempts={check_attempts}")
    
    if not captcha_id or not user_input:
        logger.warning(f"Invalid input: captcha_id='{captcha_id}', user_input='{user_input}'")
        return False
    
    # 检查尝试次数
    if check_attempts:
        attempts_key = f"captcha_attempts_{captcha_id}"
        attempts = cache.get(attempts_key, 0)
        
        logger.debug(f"Captcha {captcha_id} attempts: {attempts}/{max_attempts}")
        
        # 如果已达到最大尝试次数，拒绝进一步尝试
        if attempts >= max_attempts:
            logger.warning(f"Captcha {captcha_id} reached max attempts ({max_attempts}). Invalidating captcha.")
            # 额外保护：超过尝试次数后直接使验证码失效
            cache.delete(captcha_id)  # 删除验证码
            cache.delete(attempts_key)  # 删除尝试计数
            return False
    
        # 增加尝试次数
        cache.incr(attempts_key)
        logger.debug(f"Incremented attempts for {captcha_id}, now: {cache.get(attempts_key)}")

    # 从缓存中获取正确的验证码
    correct_captcha = cache.get(captcha_id)
    
    if not correct_captcha:
        logger.warning(f"Correct captcha not found or expired: {captcha_id}")
        return False  # 验证码已过期或不存在
    
    logger.debug(f"Retrieved correct captcha for {captcha_id}: {correct_captcha}")

    # 验证用户输入（不区分大小写）
    is_valid = correct_captcha.lower() == user_input.lower()
    logger.info(f"Captcha verification result for {captcha_id}: {is_valid} (input: {user_input}, expected: {correct_captcha})")
    
    # 如果验证成功且需要消费（一次性使用），则删除缓存中的验证码
    if is_valid and consume:
        logger.info(f"Consuming captcha {captcha_id} (deleting from cache)")
        cache.delete(captcha_id)
        cache.delete(f"captcha_attempts_{captcha_id}")  # 同时删除尝试计数
        logger.debug(f"Captcha {captcha_id} consumed and removed from cache")
    
    # 如果验证失败且已达到最大尝试次数，删除验证码以强制用户重新获取
    if not is_valid and check_attempts:
        attempts_key = f"captcha_attempts_{captcha_id}"
        current_attempts = cache.get(attempts_key, 0)
        if current_attempts >= max_attempts:
            logger.warning(f"Failed attempt reached max limit for {captcha_id}. Invalidating captcha.")
            cache.delete(captcha_id)
            cache.delete(attempts_key)

    return is_valid


def get_captcha_image(request, captcha_id):
    """
    获取验证码图片的视图函数
    
    Args:
        request: HTTP请求对象
        captcha_id: 验证码ID
    
    Returns:
        HTTP响应对象，包含验证码图片
    """
    logger.debug(f"Serving captcha image: {captcha_id}")
    
    if not captcha_id:
        # 如果没有提供captcha_id，则生成一个新的
        result = generate_captcha()
        captcha_id = result['captcha_id']
        image_data = result['image_data']
    else:
        # 如果提供了captcha_id，检查它是否存在
        captcha_text = cache.get(captcha_id)
        if not captcha_text:
            logger.warning(f"Requested captcha not found: {captcha_id}, generating new one")
            # 如果不存在，生成新的
            result = generate_captcha()
            captcha_id = result['captcha_id']
            image_data = result['image_data']
        else:
            # 如果存在，重新生成图片（但保持相同的文本）
            captcha_text, image_data = generate_captcha_image()
            # 更新缓存中的验证码，以防用户多次请求同一ID
            cache.set(captcha_id, captcha_text.lower(), 300)
            # 重置尝试次数
            attempts_key = f"captcha_attempts_{captcha_id}"
            current_attempts = cache.get(attempts_key, 0)
            cache.set(attempts_key, current_attempts, 300)
            logger.debug(f"Refreshed captcha image for {captcha_id}, attempts: {current_attempts}")
    
    return HttpResponse(image_data, content_type='image/png')