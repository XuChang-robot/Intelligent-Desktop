# 天气查询工具

import requests
import os
from typing import Dict, Any
from user_config.config import get_config


def get_public_ip() -> str:
    """获取当前公网IP地址
    
    Returns:
        公网IP地址字符串，如果获取失败返回None
    """
    try:
        # 使用多个IP查询服务，提高成功率
        ip_services = [
            'https://icanhazip.com',
            'https://ipapi.co/ip/',
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip:
                        return ip
            except Exception:
                continue
        
        return None
    except Exception as e:
        print(f"获取公网IP失败: {e}")
        return None


def get_weather_api_config():
    """获取天气API配置
    
    优先级：环境变量 > 配置文件 > 默认值
    
    Returns:
        (user_id, api_key)
    """
    user_id = os.getenv('INTERFACEBOX_API_USER_ID', '')
    if not user_id:
        user_id = get_config('interfacebox.api.user_id', '')
    
    api_key = os.getenv('INTERFACEBOX_API_KEY', '')
    if not api_key:
        api_key = get_config('interfacebox.api.api_key', '')
    
    return user_id, api_key


def parse_hourly_temperature(hourly_data: list) -> tuple:
    """从小时预报数据中解析日内最高温和最低温
    
    Args:
        hourly_data: 小时预报数据列表，每个元素包含"气温"字段
        
    Returns:
        (最高温度, 最低温度) 元组，如果解析失败返回 (None, None)
    """
    if not hourly_data:
        return None, None
    
    temperatures = []
    for hour in hourly_data:
        temp_str = hour.get('气温', '')
        if temp_str:
            try:
                temp = float(temp_str.replace('℃', '').strip())
                temperatures.append(temp)
            except (ValueError, AttributeError):
                continue
    
    if not temperatures:
        return None, None
    
    return max(temperatures), min(temperatures)


def query_ip_weather(detail_level: str = "simple", ip: str = None, day: int = None, hourtype: int = None, suntimetype: int = None, dkey: str = None, uip: str = None) -> Dict[str, Any]:
    """根据当前IP地址自动查询天气信息
    
    包括实时天气、7天预报、小时预报、日出日落时间和气象预警。
    
    Args:
        detail_level: 信息详细程度，"simple"或"detailed"
        ip: 要查询的ip地址，如不传则自动获取接口调用IP
        day: 查询天数，可传1到7，代表1到7天内天气预报，默认1
        hourtype: 是否返回时段天气预报，0=不返回，1=返回。默认0
        suntimetype: 是否返回7天日出日落详细时间，0=不返回，1=返回。默认0
        dkey: 动态秘钥（可选），用于客户端直接调用接口的场景
        uip: 用户IP（可选），用于后台统计IP地域分布、ISP运营商、时段IP数统计等
    
    Returns:
        天气查询结果字典
    """
    user_id, api_key = get_weather_api_config()
    
    # 如果没有提供IP，自动获取公网IP
    if not ip:
        ip = get_public_ip()
        if not ip:
            return {
                "success": False,
                "message": "无法获取公网IP地址，请检查网络连接"
            }
    
    url = f'https://cn.apihz.cn/api/tianqi/tqybip.php?id={user_id}&key={api_key}'
    
    if ip:
        url += f'&ip={ip}'
    if day is not None:
        url += f'&day={day}'
    if hourtype is not None:
        url += f'&hourtype={hourtype}'
    if suntimetype is not None:
        url += f'&suntimetype={suntimetype}'
    if dkey:
        url += f'&dkey={dkey}'
    if uip:
        url += f'&uip={uip}'
    
    response = requests.get(url)
    data = response.json()
    
    if data.get('code') == 200:
        location_info = f"{data.get('guo', '中国')} {data.get('sheng', '')} {data.get('shi', '')} {data.get('name', '')}"
        
        now = data.get('nowinfo', {})
        current_temp = now.get('temperature', '未知')
        feel_temp = now.get('feelst', '未知')
        humidity = now.get('humidity', '未知')
        wind_dir = now.get('windDirection', '未知')
        wind_dir_degree = now.get('windDirectionDegree', '未知')
        wind_scale = now.get('windScale', '未知')
        wind_speed = now.get('windSpeed', '未知')
        precipitation = now.get('precipitation', '未知')
        pressure = now.get('pressure', '未知')
        update_time = now.get('uptime', data.get('uptime', '未知'))
        
        today_weather = data.get('weather1', '未知')
        tomorrow_weather = data.get('weather2', '未知')
        
        hourly_data = data.get('hour1', [])
        today_temp_high, today_temp_low = parse_hourly_temperature(hourly_data)
        
        if today_temp_high is None:
            today_temp_high = data.get('wd1', '未知')
        if today_temp_low is None:
            today_temp_low = data.get('wd2', '未知')
        
        formatted_message = f"📍 {location_info}\n\n"
        formatted_message += f"🌡️ 当前温度: {current_temp}℃ (体感 {feel_temp}℃)\n"
        formatted_message += f"💨 风向: {wind_dir} ({wind_dir_degree}°)，风力: {wind_scale}，风速: {wind_speed}m/s\n"
        formatted_message += f"💧 湿度: {humidity}%\n"
        formatted_message += f"🌧️ 降水量: {precipitation}mm\n"
        formatted_message += f"🌊 气压: {pressure}百帕\n"
        formatted_message += f"🕐 更新时间: {update_time}\n\n"
        formatted_message += f"☀️ 今天: {today_weather}，{today_temp_high}℃/{today_temp_low}℃\n"
        formatted_message += f"🌙 明天: {tomorrow_weather}"
        
        result = {
            "success": True,
            "formatted_message": formatted_message,
            "location": {
                "country": data.get('guo', '中国'),
                "province": data.get('sheng', ''),
                "city": data.get('shi', ''),
                "district": data.get('name', ''),
                "longitude": data.get('lon', ''),
                "latitude": data.get('lat', '')
            },
            "current": {
                "temperature": current_temp,
                "feel_temperature": feel_temp,
                "humidity": humidity,
                "wind_direction": wind_dir,
                "wind_direction_degree": wind_dir_degree,
                "wind_scale": wind_scale,
                "wind_speed": wind_speed,
                "precipitation": precipitation,
                "pressure": pressure,
                "update_time": update_time
            },
            "today_tomorrow": {
                "today_weather": today_weather,
                "today_weather_img": data.get('weather1img', ''),
                "today_temp_high": today_temp_high,
                "today_temp_low": today_temp_low,
                "today_wind_direction": data.get('winddirection1', ''),
                "today_wind_scale": data.get('windleve1', ''),
                "tomorrow_weather": tomorrow_weather,
                "tomorrow_weather_img": data.get('weather2img', ''),
                "tomorrow_wind_direction": data.get('winddirection2', ''),
                "tomorrow_wind_scale": data.get('windleve2', '')
            }
        }
        
        if data.get('alarm'):
            alarm_data = data.get('alarm')
            # 尝试解析alarm字段，只提取title和生效时间
            if isinstance(alarm_data, dict):
                title = alarm_data.get('title', '')
                effective = alarm_data.get('effective', '')
                if title:
                    alarm_message = f"⚠️ 预警: {title}"
                    if effective:
                        alarm_message += f"\n生效时间: {effective}"
                    formatted_message += f"\n\n{alarm_message}"
                    result["alarm"] = alarm_message
            elif isinstance(alarm_data, str):
                # 如果是字符串，尝试解析JSON
                try:
                    import json
                    alarm_dict = json.loads(alarm_data)
                    title = alarm_dict.get('title', '')
                    effective = alarm_dict.get('effective', '')
                    if title:
                        alarm_message = f"⚠️ 预警: {title}"
                        if effective:
                            alarm_message += f"\n生效时间: {effective}"
                        formatted_message += f"\n\n{alarm_message}"
                        result["alarm"] = alarm_message
                    else:
                        # 如果解析失败，直接显示原始字符串
                        formatted_message += f"\n\n⚠️ 预警信息: {alarm_data}"
                        result["alarm"] = alarm_data
                except (json.JSONDecodeError, ValueError):
                    # 如果不是JSON，直接显示原始字符串
                    formatted_message += f"\n\n⚠️ 预警信息: {alarm_data}"
                    result["alarm"] = alarm_data
        
        if detail_level == "detailed":
            result["forecast"] = []
            result["hourly"] = data.get('hour1', [])
            result["sunrise_sunset"] = data.get('suntimes', [])
            
            for i in range(1, 8):
                day_key = f'weatherday{i}'
                day_data = data.get(day_key, {})
                
                if day_data:
                    result["forecast"].append({
                        "date": day_data.get('date', ''),
                        "date_formatted": day_data.get('date_formatted', ''),
                        "weekday": day_data.get('weekday', ''),
                        "weekday_cn": day_data.get('weekday_cn', ''),
                        "day_weather": day_data.get('weather1', ''),
                        "night_weather": day_data.get('weather2', ''),
                        "day_temp_high": day_data.get('wd1', ''),
                        "night_temp_low": day_data.get('wd2', ''),
                        "wind_direction": day_data.get('winddirection', ''),
                        "wind_scale": day_data.get('windleve', '')
                    })
            
            formatted_message += "\n\n📅 未来7天预报:\n"
            for day in result["forecast"][:7]:
                date_display = day.get('date_formatted', '') or day.get('date', '')
                formatted_message += f"• {date_display} ({day['weekday_cn']}): {day['day_weather']}转{day['night_weather']}, {day['day_temp_high']}℃/{day['night_temp_low']}℃, {day['wind_direction']} {day['wind_scale']}\n"
            
            if result["hourly"]:
                formatted_message += "\n⏰ 24小时预报:\n"
                for hour in result["hourly"][:24]:
                    formatted_message += f"• {hour.get('时间', '')}: {hour.get('天气', '')}, {hour.get('气温', '')}, {hour.get('风向', '')} {hour.get('风速', '')}\n"
            
            if result["sunrise_sunset"]:
                formatted_message += "\n🌅 日出日落时间:\n"
                for day_info in result["sunrise_sunset"][:7]:
                    date_display = day_info.get('date_formatted', '') or day_info.get('date', '')
                    formatted_message += f"• {date_display}: 日出 {day_info.get('sunrise', '')}, 日落 {day_info.get('sunset', '')}, 白昼 {day_info.get('day_length', '')}, 夜晚 {day_info.get('night_length', '')}\n"
        
        result["formatted_message"] = formatted_message
        return result
    else:
        return {
            "success": False,
            "message": f"请求失败: {data.get('msg', '未知错误')}"
        }


def query_domestic_weather(province: str, city: str, detail_level: str = "simple", day: int = None, hourtype: int = None, suntimetype: int = None, dkey: str = None, uip: str = None) -> Dict[str, Any]:
    """查询中国境内指定省份和城市的天气
    
    Args:
        province: 省份名称
        city: 城市名称
        detail_level: 信息详细程度，"simple"或"detailed"
        day: 查询天数，可传1到7，代表1到7天内天气预报，默认1
        hourtype: 是否返回时段天气预报，0=不返回，1=返回。默认0
        suntimetype: 是否返回7天日出日落详细时间，0=不返回，1=返回。默认0
        dkey: 动态秘钥（可选），用于客户端直接调用接口的场景
        uip: 用户IP（可选），用于后台统计IP地域分布、ISP运营商、时段IP数统计等
    
    Returns:
        天气查询结果字典
    """
    user_id, api_key = get_weather_api_config()
    
    url = f'https://cn.apihz.cn/api/tianqi/tqyb.php?id={user_id}&key={api_key}&sheng={province}&place={city}'
    
    if day is not None:
        url += f'&day={day}'
    if hourtype is not None:
        url += f'&hourtype={hourtype}'
    if suntimetype is not None:
        url += f'&suntimetype={suntimetype}'
    if dkey:
        url += f'&dkey={dkey}'
    if uip:
        url += f'&uip={uip}'
    
    response = requests.get(url)
    data = response.json()
    
    if data.get('code') == 200:
        location_info = f"{data.get('guo', '中国')} {data.get('sheng', '')} {data.get('shi', '')} {data.get('name', '')}"
        
        now = data.get('nowinfo', {})
        current_temp = now.get('temperature', '未知')
        feel_temp = now.get('feelst', '未知')
        humidity = now.get('humidity', '未知')
        wind_dir = now.get('windDirection', '未知')
        wind_dir_degree = now.get('windDirectionDegree', '未知')
        wind_scale = now.get('windScale', '未知')
        wind_speed = now.get('windSpeed', '未知')
        precipitation = now.get('precipitation', '未知')
        pressure = now.get('pressure', '未知')
        update_time = now.get('uptime', data.get('uptime', '未知'))
        
        today_weather = data.get('weather1', '未知')
        tomorrow_weather = data.get('weather2', '未知')
        
        hourly_data = data.get('hour1', [])
        today_temp_high, today_temp_low = parse_hourly_temperature(hourly_data)
        
        if today_temp_high is None:
            today_temp_high = data.get('wd1', '未知')
        if today_temp_low is None:
            today_temp_low = data.get('wd2', '未知')
        
        formatted_message = f"📍 {location_info}\n\n"
        formatted_message += f"🌡️ 当前温度: {current_temp}℃ (体感 {feel_temp}℃)\n"
        formatted_message += f"💨 风向: {wind_dir} ({wind_dir_degree}°)，风力: {wind_scale}，风速: {wind_speed}m/s\n"
        formatted_message += f"💧 湿度: {humidity}%\n"
        formatted_message += f"🌧️ 降水量: {precipitation}mm\n"
        formatted_message += f"🌊 气压: {pressure}百帕\n"
        formatted_message += f"🕐 更新时间: {update_time}\n\n"
        formatted_message += f"☀️ 今天: {today_weather}，{today_temp_high}℃/{today_temp_low}℃\n"
        formatted_message += f"🌙 明天: {tomorrow_weather}"
        
        result = {
            "success": True,
            "formatted_message": formatted_message,
            "location": {
                "country": data.get('guo', '中国'),
                "province": data.get('sheng', ''),
                "city": data.get('shi', ''),
                "district": data.get('name', ''),
                "longitude": data.get('lon', ''),
                "latitude": data.get('lat', '')
            },
            "current": {
                "temperature": current_temp,
                "feel_temperature": feel_temp,
                "humidity": humidity,
                "wind_direction": wind_dir,
                "wind_direction_degree": wind_dir_degree,
                "wind_scale": wind_scale,
                "wind_speed": wind_speed,
                "precipitation": precipitation,
                "pressure": pressure,
                "update_time": update_time
            },
            "today_tomorrow": {
                "today_weather": today_weather,
                "today_weather_img": data.get('weather1img', ''),
                "today_temp_high": today_temp_high,
                "today_temp_low": today_temp_low,
                "today_wind_direction": data.get('winddirection1', ''),
                "today_wind_scale": data.get('windleve1', ''),
                "tomorrow_weather": tomorrow_weather,
                "tomorrow_weather_img": data.get('weather2img', ''),
                "tomorrow_wind_direction": data.get('winddirection2', ''),
                "tomorrow_wind_scale": data.get('windleve2', '')
            }
        }
        
        if data.get('alarm'):
            alarm_data = data.get('alarm')
            # 尝试解析alarm字段，只提取title和生效时间
            if isinstance(alarm_data, dict):
                title = alarm_data.get('title', '')
                effective = alarm_data.get('effective', '')
                if title:
                    alarm_message = f"⚠️ 预警: {title}"
                    if effective:
                        alarm_message += f"\n生效时间: {effective}"
                    formatted_message += f"\n\n{alarm_message}"
                    result["alarm"] = alarm_message
            elif isinstance(alarm_data, str):
                # 如果是字符串，尝试解析JSON
                try:
                    import json
                    alarm_dict = json.loads(alarm_data)
                    title = alarm_dict.get('title', '')
                    effective = alarm_dict.get('effective', '')
                    if title:
                        alarm_message = f"⚠️ 预警: {title}"
                        if effective:
                            alarm_message += f"\n生效时间: {effective}"
                        formatted_message += f"\n\n{alarm_message}"
                        result["alarm"] = alarm_message
                    else:
                        # 如果解析失败，直接显示原始字符串
                        formatted_message += f"\n\n⚠️ 预警信息: {alarm_data}"
                        result["alarm"] = alarm_data
                except (json.JSONDecodeError, ValueError):
                    # 如果不是JSON，直接显示原始字符串
                    formatted_message += f"\n\n⚠️ 预警信息: {alarm_data}"
                    result["alarm"] = alarm_data
        
        if detail_level == "detailed":
            result["forecast"] = []
            result["hourly"] = data.get('hour1', [])
            result["sunrise_sunset"] = data.get('suntimes', [])
            
            for i in range(1, 8):
                day_key = f'weatherday{i}'
                day_data = data.get(day_key, {})
                
                if day_data:
                    result["forecast"].append({
                        "date": day_data.get('date', ''),
                        "date_formatted": day_data.get('date_formatted', ''),
                        "weekday": day_data.get('weekday', ''),
                        "weekday_cn": day_data.get('weekday_cn', ''),
                        "day_weather": day_data.get('weather1', ''),
                        "night_weather": day_data.get('weather2', ''),
                        "day_temp_high": day_data.get('wd1', ''),
                        "night_temp_low": day_data.get('wd2', ''),
                        "wind_direction": day_data.get('winddirection', ''),
                        "wind_scale": day_data.get('windleve', '')
                    })
            
            formatted_message += "\n\n📅 未来7天预报:\n"
            for day in result["forecast"][:7]:
                date_display = day.get('date_formatted', '') or day.get('date', '')
                formatted_message += f"• {date_display} ({day['weekday_cn']}): {day['day_weather']}转{day['night_weather']}, {day['day_temp_high']}℃/{day['night_temp_low']}℃, {day['wind_direction']} {day['wind_scale']}\n"
            
            if result["hourly"]:
                formatted_message += "\n⏰ 24小时预报:\n"
                for hour in result["hourly"][:24]:
                    formatted_message += f"• {hour.get('时间', '')}: {hour.get('天气', '')}, {hour.get('气温', '')}, {hour.get('风向', '')} {hour.get('风速', '')}\n"
            
            if result["sunrise_sunset"]:
                formatted_message += "\n🌅 日出日落时间:\n"
                for day_info in result["sunrise_sunset"][:7]:
                    date_display = day_info.get('date_formatted', '') or day_info.get('date', '')
                    formatted_message += f"• {date_display}: 日出 {day_info.get('sunrise', '')}, 日落 {day_info.get('sunset', '')}, 白昼 {day_info.get('daytime', '')}, 夜晚 {day_info.get('nighttime', '')}\n"
        
        result["formatted_message"] = formatted_message
        return result
    else:
        return {
            "success": False,
            "message": f"请求失败: {data.get('msg', '未知错误')}"
        }


def query_foreign_weather(city: str, detail_level: str = "simple", dkey: str = None, uip: str = None) -> Dict[str, Any]:
    """查询国外主要城市的天气
    
    Args:
        city: 城市名称
        detail_level: 信息详细程度，"simple"或"detailed"
        dkey: 动态秘钥（可选），用于客户端直接调用接口的场景
        uip: 用户IP（可选），用于后台统计IP地域分布、ISP运营商、时段IP数统计等
    
    Returns:
        天气查询结果字典
    """
    user_id, api_key = get_weather_api_config()
    
    url = f'http://101.35.2.25/api/tianqi/tqybun.php?id={user_id}&key={api_key}&city={city}'
    
    if dkey:
        url += f'&dkey={dkey}'
    if uip:
        url += f'&uip={uip}'
    
    print(f"查询国外天气URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"API响应状态码: {response.status_code}")
        print(f"API响应内容: {response.text[:500]}")  # 只打印前500个字符
        
        if response.status_code != 200:
            return {
                "success": False,
                "message": f"API请求失败，状态码: {response.status_code}, 响应: {response.text[:200]}"
            }
        
        data = response.json()
        print(f"国外天气API返回: {data}")
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "API请求超时"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "message": f"API请求异常: {str(e)}"
        }
    except ValueError as e:
        return {
            "success": False,
            "message": f"API返回数据格式错误: {str(e)}, 响应内容: {response.text[:200]}"
        }
    
    if data.get('code') == 200:
        print(f"API返回的完整数据: {data}")
        
        location_info = f"{data.get('guo', '')} {data.get('city', '')}"
        print(f"位置信息: {location_info}")
        
        formatted_message = f"📍 {location_info}\n\n"
        
        forecast_list = []
        for i in range(1, 7):
            day_key = f'weatherday{i}'
            day_data = data.get(day_key, {})
            print(f"检查 {day_key}: {day_data}")
            
            if day_data:
                forecast_list.append({
                    "date": day_data.get('date', ''),
                    "date_formatted": day_data.get('date_formatted', ''),
                    "weekday": day_data.get('weekday', ''),
                    "weekday_cn": day_data.get('weekday_cn', ''),
                    "day_weather": day_data.get('weather1', ''),
                    "night_weather": day_data.get('weather2', ''),
                    "day_temp_high": day_data.get('wd1', ''),
                    "night_temp_low": day_data.get('wd2', ''),
                    "wind_direction": day_data.get('winddirection', ''),
                    "wind_scale": day_data.get('windleve', '')
                })
        
        print(f"forecast_list长度: {len(forecast_list)}")
        print(f"forecast_list内容: {forecast_list}")
        
        if forecast_list:
            if detail_level == "simple":
                # 只显示今天和明天
                today = forecast_list[0]
                tomorrow = forecast_list[1] if len(forecast_list) > 1 else None
                
                formatted_message += f"☀️ 今天: {today['day_weather']}转{today['night_weather']}, {today['day_temp_high']}℃/{today['night_temp_low']}℃, {today['wind_direction']} {today['wind_scale']}\n"
                if tomorrow:
                    formatted_message += f"🌙 明天: {tomorrow['day_weather']}转{tomorrow['night_weather']}, {tomorrow['day_temp_high']}℃/{tomorrow['night_temp_low']}℃, {tomorrow['wind_direction']} {tomorrow['wind_scale']}"
            else:
                # 显示全部6天预报
                formatted_message += "📅 未来6天预报:\n"
                for day in forecast_list:
                    formatted_message += f"• {day['date_formatted']} ({day['weekday_cn']}): {day['day_weather']}转{day['night_weather']}, {day['day_temp_high']}℃/{day['night_temp_low']}℃, {day['wind_direction']} {day['wind_scale']}\n"
            
            result = {
                "success": True,
                "formatted_message": formatted_message,
                "location": {
                    "country": data.get('guo', ''),
                    "city": data.get('city', '')
                },
                "forecast": forecast_list if detail_level == "detailed" else forecast_list[:2]
            }
            
            return result
        else:
            return {
                "success": False,
                "message": "未获取到天气数据"
            }
    else:
        return {
            "success": False,
            "message": f"请求失败: {data.get('msg', '未知错误')}"
        }


def register_weather_query_tools(mcp):
    """注册天气查询工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
    """
    
    @mcp.tool()
    async def weather_query(operation: str, detail_level: str = "simple", province: str = None, city: str = None, ip: str = None, day: int = None, hourtype: int = None, suntimetype: int = None, dkey: str = None, uip: str = None) -> Dict[str, Any]:
        """天气查询工具
        
        用于查询天气信息，包括实时天气、7天预报、小时预报、日出日落时间和气象预警等。

        根据operation参数执行不同类型的天气查询：
        - "ip_weather": 根据当前IP地址自动查询天气信息，。如果不提供ip参数，会自动获取当前公网IP地址。
        - "domestic_weather": 查询中国境内指定省份和城市的天气，支持7天预报
        - "foreign_weather": 查询国外主要城市的天气，支持6天预报
        
        注意：
        如果参数只提供了中国国内的城市，则需要自动补全省份参数
        例如："哈尔滨天气" -> province="黑龙江", city="哈尔滨"

        Args:
            operation: 操作类型，可选值：
                - "ip_weather": IP地址天气查询，适用于用户没有指定具体地点的天气查询，如"今天天气如何"、"天气怎么样"等。
                - "domestic_weather": 适用于中国国内天气查询
                - "foreign_weather": 适用于中国以外的天气查询
            detail_level: 信息详细程度，可选值：
                - "simple": 简洁信息（默认），只返回当前天气和今天明天的天气
                - "detailed": 详细信息，返回完整数据包括预报等
            province: 省份名称（仅domestic_weather需要，必填参数），例如："北京"、"上海"、"广东"、"湖南"
            city: 城市名称（domestic_weather和foreign_weather需要），例如："朝阳"、"浦东"、"深圳"、"东京"、"纽约"
            ip: IP地址（仅ip_weather），要查询的ip地址，如不传则自动获取当前公网IP地址
            day: 查询天数（ip_weather和domestic_weather），可传1到7，代表1到7天内天气预报，默认1
            hourtype: 是否返回时段天气预报（ip_weather和domestic_weather），0=不返回，1=返回。默认0
            suntimetype: 是否返回7天日出日落详细时间（ip_weather和domestic_weather），0=不返回，1=返回。默认0
        
        Returns:
            {
                "success": True/False,
                "formatted_message": "格式化的自然语言描述",
                "location": {...},
                "current": {...},
                "today_tomorrow": {...},
                "forecast": [...],
                "hourly": [...],
                "sunrise_sunset": [...],
                "alarm": "...",
                "message": "错误信息（如果失败）"
            }
        
        Examples:
            - 查询当前IP地址天气（包含小时预报和日出日落）: weather_query("ip_weather", "detailed", hourtype=1, suntimetype=1)
            - 根据提供的中国国内城市自动补全省份："长春市天气" -> province="吉林", city="长春"
        """
        try:
            print(f"weather_query被调用，参数: operation={operation}, detail_level={detail_level}, province={province}, city={city}, ip={ip}, day={day}, hourtype={hourtype}, suntimetype={suntimetype}")
            
            if operation == "ip_weather":
                return query_ip_weather(detail_level, ip, day, hourtype, suntimetype, dkey, uip)
            elif operation == "domestic_weather":
                if not province or not city:
                    return {
                        "success": False,
                        "message": "国内天气查询需要提供province和city参数"
                    }
                return query_domestic_weather(province, city, detail_level, day, hourtype, suntimetype, dkey, uip)
            elif operation == "foreign_weather":
                if not city:
                    return {
                        "success": False,
                        "message": "国外天气查询需要提供city参数"
                    }
                
                unsupported_params = []
                if day is not None:
                    unsupported_params.append("day")
                if hourtype is not None:
                    unsupported_params.append("hourtype")
                if suntimetype is not None:
                    unsupported_params.append("suntimetype")
                
                print(f"调用query_foreign_weather，参数: city={city}, detail_level={detail_level}")
                result = query_foreign_weather(city, detail_level, dkey, uip)
                print(f"query_foreign_weather返回: {result}")
                
                if unsupported_params and result.get("success"):
                    warning_msg = f"\n\n⚠️ 注意：国外天气API不支持以下参数：{', '.join(unsupported_params)}。这些参数已被忽略。国外天气API仅支持dkey和uip可选参数。"
                    result["formatted_message"] += warning_msg
                    print(f"⚠️ 国外天气API不支持以下参数：{', '.join(unsupported_params)}")
                
                return result
            else:
                return {
                    "success": False,
                    "message": f"不支持的操作类型: {operation}，支持的类型: ip_weather, domestic_weather, foreign_weather"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"程序执行出错: {str(e)}"
            }
