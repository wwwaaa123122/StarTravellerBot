# -*- coding: utf-8 -*-
"""天气插件 - 适配 QQ 开放平台"""

import httpx
import logging
_logger = logging.getLogger("weather")
import logging

TRIGGHT_KEYWORD = "天气"
HELP_MESSAGE = "天气 <城市> -> 查询天气信息"

# 天气描述中英文映射
WEATHER_CN = {
    "Clear": "晴天",
    "Sunny": "晴天",
    "Partly cloudy": "多云",
    "Partly Cloudy": "多云",
    "Cloudy": "阴天",
    "Overcast": "阴天",
    "Mist": "薄雾",
    "Fog": "雾",
    "Light rain": "小雨",
    "Light Rain": "小雨",
    "Moderate rain": "中雨",
    "Heavy rain": "大雨",
    "Light snow": "小雪",
    "Moderate snow": "中雪",
    "Heavy snow": "大雪",
    "Thundery outbreaks possible": "可能有雷阵雨",
    "Patchy rain possible": "可能有阵雨",
    "Patchy snow possible": "可能有阵雪",
    "Light rain shower": "小阵雨",
    "Moderate or heavy rain shower": "中到大阵雨",
    "Light sleet": "雨夹雪",
    "Moderate or heavy sleet": "中到大雨夹雪",
    "Patchy light drizzle": "零星小雨",
    "Light drizzle": "毛毛雨",
    "Patchy light rain": "零星小雨",
    "Patchy rain nearby": "附近有阵雨",
    "Torrential rain shower": "暴雨",
}


def _translate_weather(desc: str) -> str:
    """翻译天气描述为中文"""
    if not desc:
        return "未知"
    
    # 尝试精确匹配
    if desc in WEATHER_CN:
        return WEATHER_CN[desc]
    
    # 尝试模糊匹配
    for en, cn in WEATHER_CN.items():
        if en.lower() in desc.lower() or desc.lower() in en.lower():
            return cn
    
    return desc


async def on_message(event, actions, **kwargs):
    """处理天气查询"""
    content = event.message if hasattr(event, 'message') else ""
    
    # 提取城市名
    if content.startswith("天气"):
        city = content[2:].strip()
    else:
        city = content.strip()
    
    if not city:
        await actions.send(content="用法: 天气 <城市名>\n例如: 天气 北京")
        return True
    
    try:
        # 使用 wttr.in API 查询天气
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://wttr.in/{city}?format=j1",
                headers={"Accept-Language": "zh-CN"}
            )
            
            if response.status_code != 200:
                await actions.send(content=f"查询天气失败: {response.status_code}")
                return True
            
            data = response.json()
            current = data.get("current_condition", [{}])[0]
            
            # 解析天气信息
            temp = current.get("temp_C", "未知")
            feels_like = current.get("FeelsLikeC", "未知")
            humidity = current.get("humidity", "未知")
            wind_speed = current.get("windspeedKmph", "未知")
            wind_dir = current.get("winddir16Point", "")
            
            # 获取中文天气描述
            weather_desc = current.get("weatherDesc", [{}])[0].get("value", "")
            zh_desc = current.get("lang_zh", [{}])[0].get("value", "")
            description = zh_desc if zh_desc else _translate_weather(weather_desc)
            
            # 获取预报
            forecast = data.get("weather", [])
            today_forecast = forecast[0] if forecast else {}
            max_temp = today_forecast.get("maxtempC", "未知")
            min_temp = today_forecast.get("mintempC", "未知")
            
            # 获取日出日落
            astronomy = today_forecast.get("astronomy", [{}])[0] if today_forecast else {}
            sunrise = astronomy.get("sunrise", "").strip()
            sunset = astronomy.get("sunset", "").strip()
            
            msg = f"""## 📍 {city} 天气

- **🌡️ 当前温度**: {temp}°C (体感 {feels_like}°C)
- **📊 温度范围**: {min_temp}°C ~ {max_temp}°C
- **💧 湿度**: {humidity}%
- **💨 风速**: {wind_speed} km/h {wind_dir}
- **🌤️ 天气**: {description}"""
            
            if sunrise and sunset:
                msg += f"\n🌅 日出: {sunrise}"
                msg += f"\n🌇 日落: {sunset}"
            
            await actions.send(content=msg)
            return True
            
    except Exception as e:
        _logger.error(f"天气查询失败 ({city}): {e}")
        await actions.send(content="查询天气出错，请稍后重试")
        return True
