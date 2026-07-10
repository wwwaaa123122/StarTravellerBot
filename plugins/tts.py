import os
import re
import gc
import asyncio

TRIGGHT_KEYWORD = "语音"
HELP_MESSAGE = "语音 <文本> -> 将文本转为语音并发送"


def sanitize_for_tts(text: str) -> str:
    """清理文本中的 markdown/颜文字，保留适合 TTS 朗读的纯文本"""
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'!?\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'[*_~]{1,2}(.*?)[*_~]{1,2}', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[\(（].*?[\)）]', '', text)
    text = re.sub(r'[\U0001F300-\U0001FAFF\U00002702-\U000027B0]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _get_tts_config(config: dict) -> dict:
    """从配置中读取 TTS 设置（参照父项目 config.Others.TTS）"""
    others = config.get("Others", {})
    tts_cfg = others.get("TTS", others.get("TTs", {}))
    if not tts_cfg:
        tts_cfg = {}
    return {
        "voice": tts_cfg.get("voiceColor", "zh-CN-XiaoyiNeural"),
        "rate": tts_cfg.get("rate", "+0%"),
        "volume": tts_cfg.get("volume", "+0%"),
        "pitch": tts_cfg.get("pitch", "+0Hz"),
    }


async def _generate_tts(text: str, config: dict) -> str:
    """使用 edge-tts 生成语音文件"""
    import edge_tts

    tts_cfg = _get_tts_config(config)
    communicate = edge_tts.Communicate(
        text,
        tts_cfg["voice"],
        rate=tts_cfg["rate"],
        volume=tts_cfg["volume"],
        pitch=tts_cfg["pitch"],
    )

    tts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tts")
    os.makedirs(tts_dir, exist_ok=True)

    tts_num = 0
    output_path = os.path.join(tts_dir, f"responseVoice_{tts_num}.wav")
    while os.path.exists(output_path):
        tts_num += 1
        output_path = os.path.join(tts_dir, f"responseVoice_{tts_num}.wav")

    await communicate.save(output_path)

    del communicate
    gc.collect()

    return output_path


async def on_message(event, actions, **kwargs):
    content = event.message if hasattr(event, 'message') else ""

    text = content
    if content.startswith("语音"):
        text = content[2:].strip()
    if not text:
        await actions.send(content="用法: 语音 <文本>\n例如: 语音 你好，欢迎使用星辰旅人")
        return True

    if len(text) > 200:
        await actions.send(content="文本过长，请控制在200字以内")
        return True

    clean_text = sanitize_for_tts(text)
    if not clean_text:
        await actions.send(content="没有可朗读的文本内容")
        return True

    config = kwargs.get('config', {})
    audio_path = None
    try:
        audio_path = await _generate_tts(clean_text, config)
        await actions.send_local_file(audio_path, file_type=3)
        await asyncio.sleep(1)
    except ImportError:
        await actions.send(content="TTS 功能不可用：缺少 edge-tts 库，请执行 pip install edge-tts")
    except Exception as e:
        await actions.send(content=f"语音生成失败: {e}")
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    return True
