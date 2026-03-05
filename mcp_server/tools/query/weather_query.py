# 工具创建规则：
# 1. 必须在文件最前面定义工具说明，包括工具名称、支持的操作类型、必需参数、可选参数、参数验证规则和返回格式
# 2. 必须定义操作类型配置（OPERATION_CONFIG或其他类似配置），包含各操作类型的描述、必需参数和可选参数
# 3. 必须实现validate_parameters函数，用于验证和调整参数，返回(调整后的参数字典, 配置错误信息)
# 4. 必须在工具函数开始时调用validate_parameters进行参数验证，如果存在config_error则返回包含config_error字段的错误结果
# 5. 必须统一返回字典格式结果，包含success字段和formatted_message字段
# 6. 配置错误时返回{"success": False, "config_error": "...", "formatted_message": "❌ 配置错误: ..."}
# 7. 执行失败时返回{"success": False, "error": "...", "formatted_message": "❌ 错误: ..."}
# 8. 成功时返回{"success": True, "result": "...", "formatted_message": "✅ ..."}
# 9. 必须包含operation参数，用于指定具体的操作类型
# 10. 只有当返回结果包含config_error字段时，行为树自动修复机制才会触发配置修复
# 11. formatted_message字段是系统返回给UI的信息，必须包含清晰的操作结果描述和状态标识
# 
# 原因：
# - 统一的参数验证机制确保LLM生成的配置能够被正确验证，避免参数错误导致执行失败
# - 统一的返回格式便于行为树自动修复机制识别配置错误和执行失败，只在配置错误时触发修复
# - 标准化的工具文档和配置格式便于维护和扩展，提高代码可读性
# - operation参数是工具操作的核心标识符，确保工具能够正确执行指定的操作
# - formatted_message字段为UI提供清晰的操作结果展示，提升用户体验


# 天气查询工具

import requests
import os
from enum import Enum
from typing import Dict, Any, Tuple, List, Optional
from pydantic import Field
from user_config.config import get_config


# 操作类型枚举
class WeatherOperationEnum(str, Enum):
    IP_WEATHER = "ip_weather"
    DOMESTIC_WEATHER = "domestic_weather"
    FOREIGN_WEATHER = "foreign_weather"

# 参数范围配置
PARAMETER_RANGES = {
    'domestic': {
        'days': {
            'min': 1, 
            'max': 7, 
            'default': 1, 
            'adjust_to_max': True,
            'warning_template': 'days参数值{value}超出国内天气API限制（1-7），将调整为7天'
        },
        'day': {
            'min': 1, 
            'max': 7, 
            'default': None, 
            'ignore_if_out_of_range': True,
            'warning_template': 'day参数值{value}超出国内天气API限制（1-7），将忽略此参数'
        }
    },
    'foreign': {
        'days': {
            'min': 1, 
            'max': 6, 
            'default': 1, 
            'adjust_to_max': True,
            'warning_template': 'days参数值{value}超出国外天气API限制（最多6天），将显示全部6天预报'
        },
        'day': {
            'min': 1, 
            'max': 6, 
            'default': None, 
            'ignore_if_out_of_range': True,
            'warning_template': 'day参数值{value}超出国外天气API限制（最多6天），将显示全部6天预报'
        }
    }
}


def validate_parameters(operation: WeatherOperationEnum, days: int = None, day: int = None, hourtype: int = None, suntimetype: int = None, province: str = None, city: str = None) -> Tuple[Dict[str, Any], List[str], Optional[str]]:
    """验证并调整参数
    
    Args:
        operation: 操作类型，"ip_weather"、"domestic_weather"或"foreign_weather"
        days: 查询天数
        day: 查询某一天的天气
        hourtype: 是否返回时段天气预报
        suntimetype: 是否返回日出日落时间
        province: 省份名称（仅domestic_weather需要）
        city: 城市名称（domestic_weather和foreign_weather需要）
    
    Returns:
        (调整后的参数字典, 警告信息列表, 配置错误信息)
    """
    params = {
        'operation': operation,
        'days': days,
        'day': day,
        'hourtype': hourtype,
        'suntimetype': suntimetype,
        'province': province,
        'city': city
    }
    
    warnings = []
    config_error = None
    
    # 验证必需参数
    if operation == WeatherOperationEnum.DOMESTIC_WEATHER:
        if not province:
            config_error = "国内天气查询需要提供province参数"
        elif not city:
            config_error = "国内天气查询需要提供city参数"
    elif operation == WeatherOperationEnum.FOREIGN_WEATHER:
        if not city:
            config_error = "国外天气查询需要提供city参数"
    
    # 如果存在配置错误，直接返回
    if config_error:
        return params, warnings, config_error
    
    # 获取对应的参数范围配置
    range_key = None
    if operation == WeatherOperationEnum.DOMESTIC_WEATHER:
        range_key = 'domestic'
    elif operation == WeatherOperationEnum.FOREIGN_WEATHER:
        range_key = 'foreign'
    elif operation == WeatherOperationEnum.IP_WEATHER:
        # IP天气查询使用国内天气的参数范围配置
        range_key = 'domestic'
    
    if not range_key:
        return params, warnings, config_error
    
    range_config = PARAMETER_RANGES[range_key]
    
    # 验证days参数
    if days is not None and 'days' in range_config:
        config = range_config['days']
        if days < config['min'] or days > config['max']:
            warnings.append(config['warning_template'].format(value=days))
            if config.get('adjust_to_max'):
                params['days'] = config['max']
    
    # 验证day参数
    if day is not None and 'day' in range_config:
        config = range_config['day']
        if day < config['min'] or day > config['max']:
            warnings.append(config['warning_template'].format(value=day))
            if config.get('ignore_if_out_of_range'):
                params['day'] = None
    
    return params, warnings, config_error


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


def _format_weather_response(data: Dict[str, Any], location_info: str, days: int = 1, day: int = None, suntimetype: int = None) -> Dict[str, Any]:
    """格式化天气响应数据
    
    Args:
        data: 天气API返回的原始数据
        location_info: 位置信息字符串
        days: 查询天数
        day: 查询某一天的天气
        suntimetype: 是否返回日出日落时间
    
    Returns:
        格式化后的天气响应字典
    """
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
    
    day_weather = data.get('weather1', '未知')
    night_weather = data.get('weather2', '未知')
    day_weather_img = data.get('weather1img', '')
    night_weather_img = data.get('weather2img', '')
    
    hourly_data = data.get('hour1', [])
    day_temp_high, day_temp_low = parse_hourly_temperature(hourly_data)
    
    if day_temp_high is None:
        day_temp_high = data.get('wd1', '未知')
    if day_temp_low is None:
        day_temp_low = data.get('wd2', '未知')
    
    formatted_message = f"📍 {location_info} 🕐更新时间: {update_time}\n"
    
    # 如果指定了day参数，只显示某一天的天气（忽略days参数）
    if day is not None and day != 1:
        # 从weatherday{day}中获取数据
        day_key = f'weatherday{day}'
        day_data = data.get(day_key, {})
        
        if day_data:
            day_weather1 = day_data.get('weather1', '未知')
            day_weather1_img = data.get(f'weather1img', '')
            day_weather2 = day_data.get('weather2', '未知')
            day_weather2_img = data.get(f'weather2img', '')
            
            day_temp_high = day_data.get('wd1', '未知')
            day_temp_low = day_data.get('wd2', '未知')
            
            day_wind_direction = day_data.get('winddirection', '')
            day_wind_scale = day_data.get('windleve', '')
            
            date_display = day_data.get('date_formatted', '')
        
        if not date_display:
            date_display = "今天" if day == 1 else "明天" if day == 2 else f"{day-1}天后"
        formatted_message += f"{date_display}: {day_weather1}{day_weather1_img}转{day_weather2}{day_weather2_img}，{day_temp_high}℃/{day_temp_low}℃\n"
        
        # 处理日出日落时间（如果suntimetype启用）
        if suntimetype == 1:
            sunrise_sunset = data.get('suntimes', [])
            if sunrise_sunset:
                formatted_message += "\n🌅 日出日落时间:\n"
                # 只显示指定天的日出日落时间
                if sunrise_sunset and day <= len(sunrise_sunset):
                    day_info = sunrise_sunset[day - 1]
                    date_display = day_info.get('date_formatted', '') or day_info.get('date', '')
                    formatted_message += f"• {date_display}: 日出 {day_info.get('sunrise', '')}, 日落 {day_info.get('sunset', '')}, 白昼 {day_info.get('daytime', '')}, 夜晚 {day_info.get('nighttime', '')}\n"
        
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
            "day": day,
            "day_weather1": day_weather1,
            "day_weather1_img": day_weather1_img,
            "day_weather2": day_weather2,
            "day_weather2_img": day_weather2_img,
            "day_temp_high": day_temp_high,
            "day_temp_low": day_temp_low,
            "day_wind_direction": day_wind_direction,
            "day_wind_scale": day_wind_scale
        }
        
        # 添加日出日落数据（如果suntimetype启用）
        if suntimetype == 1:
            sunrise_sunset = data.get('suntimes', [])
            if sunrise_sunset and day <= len(sunrise_sunset):
                day_info = sunrise_sunset[day - 1]
                result["sunrise_sunset"] = [day_info]
    else:
        # 显示当前天气和指定天数的预报（使用days参数）
        formatted_message += f"今天: {day_weather}{day_weather_img}转{night_weather}{night_weather_img}，最高{day_temp_high}℃/最低{day_temp_low}℃\n"
        formatted_message += f"🌡️ 当前温度: {current_temp}℃ (体感 {feel_temp}℃)\n"
        formatted_message += f"💨 风向: {wind_dir} ({wind_dir_degree}°)，风力: {wind_scale}，风速: {wind_speed}m/s\n"
        formatted_message += f"💧 湿度: {humidity}%\n"
        formatted_message += f"🌧️ 降水量: {precipitation}mm\n"
        formatted_message += f"🌊 气压: {pressure}百帕\n"
        
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
            "day_night": {
                    "day_weather": day_weather,
                    "day_weather_img": day_weather_img,
                    "day_temp_high": day_temp_high,
                    "day_temp_low": day_temp_low,
                    "day_wind_direction": data.get('winddirection1', ''),
                    "day_wind_scale": data.get('windleve1', ''),
                    "night_weather": night_weather,
                    "night_weather_img": night_weather_img,
                    "night_wind_direction": data.get('winddirection2', ''),
                    "night_wind_scale": data.get('windleve2', '')
                },
                "weather_images": {
                    "day": day_weather_img,
                    "night": night_weather_img
                }
            }
        
        # 处理预警信息
        if data.get('alarm'):
            alarm_data = data.get('alarm')
            if isinstance(alarm_data, dict):
                title = alarm_data.get('title', '')
                effective = alarm_data.get('effective', '')
                if title:
                    alarm_message = f"⚠️预警: {title}"
                    if effective:
                        alarm_message += f" 🕐生效时间{effective}"
                    formatted_message += f"\n{alarm_message}"
                    result["alarm"] = alarm_message
            elif isinstance(alarm_data, str):
                try:
                    import json
                    alarm_dict = json.loads(alarm_data)
                    title = alarm_dict.get('title', '')
                    effective = alarm_dict.get('effective', '')
                    if title:
                        alarm_message = f"⚠️预警: {title}"
                        if effective:
                            alarm_message += f" 🕐生效时间{effective}"
                        formatted_message += f"\n{alarm_message}"
                        result["alarm"] = alarm_message
                    else:
                        formatted_message += f"\n⚠️预警信息: {alarm_data}"
                        result["alarm"] = alarm_data
                except (json.JSONDecodeError, ValueError):
                    formatted_message += f"\n⚠️预警信息: {alarm_data}"
                    result["alarm"] = alarm_data
        
        # 处理多天预报
        if days > 1:
            formatted_message += "\n📅 天气预报:\n"
            for i in range(2, days + 1):
                day_key = f'weatherday{i}'
                day_data = data.get(day_key, {})
                
                if day_data:
                    day_weather = day_data.get('weather1', '未知')
                    day_weather_img = day_data.get('weather1img', '')
                    day_temp_high = day_data.get('wd1', '未知')
                    day_temp_low = day_data.get('wd2', '未知')
                else:
                    day_weather = data.get(f'weather{i}', '未知')
                    day_weather_img = data.get(f'weather{i}img', '')
                    day_temp_high = data.get(f'wd{2*i-1}', '未知')
                    day_temp_low = data.get(f'wd{2*i}', '未知')
                
                # 尝试从weatherday{i}中获取日期
                date_display = ''
                if day_data:
                    date_display = day_data.get('date_formatted', '')
                    if not date_display:
                        date_display = day_data.get('date', '')
                
                # 如果仍然没有日期信息，使用原来的显示方式
                if not date_display:
                    date_display = "今天" if i == 1 else "明天" if i == 2 else f"{i-1}天后"
                
                formatted_message += f"• {date_display}: {day_weather}{day_weather_img}转{night_weather}{night_weather_img}，白天{day_temp_high}℃/夜晚{day_temp_low}℃\n"
        
        # 处理日出日落时间（如果suntimetype启用）
        if suntimetype == 1:
            sunrise_sunset = data.get('suntimes', [])
            if sunrise_sunset:
                formatted_message += "\n🌅 日出日落时间:\n"
                
                # 根据day参数决定显示哪些天的日出日落时间
                if day is not None:
                    # 只显示指定天的日出日落时间
                    if sunrise_sunset and day <= len(sunrise_sunset):
                        day_info = sunrise_sunset[day - 1]
                        date_display = day_info.get('date_formatted', '') or day_info.get('date', '')
                        formatted_message += f"• {date_display}: 日出 {day_info.get('sunrise', '')}, 日落 {day_info.get('sunset', '')}, 白昼 {day_info.get('daytime', '')}, 夜晚 {day_info.get('nighttime', '')}\n"
                        result["sunrise_sunset"] = [day_info]
                else:
                    # 按照days参数显示指定天数的日出日落时间
                    for day_info in sunrise_sunset[:days]:
                        date_display = day_info.get('date_formatted', '') or day_info.get('date', '')
                        formatted_message += f"• {date_display}: 日出 {day_info.get('sunrise', '')}, 日落 {day_info.get('sunset', '')}, 白昼 {day_info.get('daytime', '')}, 夜晚 {day_info.get('nighttime', '')}\n"
                    result["sunrise_sunset"] = sunrise_sunset[:days]
    
    result["formatted_message"] = formatted_message
    return result

def query_ip_weather(ip: str = None, days: int = 1, day: int = None, suntimetype: int = None, dkey: str = None, uip: str = None) -> Dict[str, Any]:
    """根据当前IP地址自动查询天气信息
    
    包括实时天气、7天预报、小时预报、日出日落时间和气象预警。
    
    Args:
        ip: 要查询的ip地址，如不传则自动获取接口调用IP
        days: 查询天数，1-7，默认1
        day: 查询某一天的天气，1-7，None表示查询所有days天
        suntimetype: 是否返回7天日出日落详细时间，0=不返回，1=返回。默认0
        dkey: 动态秘钥（可选），用于客户端直接调用接口的场景
        uip: 用户IP（可选），用于后台统计IP地域分布、ISP运营商、时段IP数统计等
    
    Returns:
        天气查询结果字典
    """
    user_id, api_key = get_weather_api_config()
    
    # 使用统一的参数验证机制，强制hourtype为1
    params, warning_params, config_error = validate_parameters('ip', days, day, 1, suntimetype, None, None)
    
    # 如果存在配置错误，返回错误
    if config_error:
        return {
            "success": False,
            "config_error": config_error
        }
    
    days = params['days']
    day = params['day']
    hourtype = 1
    suntimetype = params['suntimetype']
    
    # 如果没有提供IP，自动获取公网IP
    if not ip:
        ip = get_public_ip()
        if not ip:
            return {
                "success": False,
                "message": "无法获取公网IP地址，请检查网络连接"
            }
    
    url = f'http://101.35.2.25/api/tianqi/tqybip.php?id={user_id}&key={api_key}'
    
    if ip:
        url += f'&ip={ip}'
    # 总是查询最大天数（7天），以提高缓存命中率
    url += f'&day=7'
    # 强制hourtype为1，因为需要小时数据去计算最高最低温
    url += f'&hourtype=1'
    if suntimetype is not None:
        url += f'&suntimetype={suntimetype}'
    if dkey:
        url += f'&dkey={dkey}'
    if uip:
        url += f'&uip={uip}'
    
    response = requests.get(url)
    data = response.json()
    
    if data.get('code') == 200:
        location_info = f"{data.get('guo', '中国')} {data.get('sheng', '')} {data.get('shi', '')}"
        result = _format_weather_response(data, location_info, days=days, day=day, suntimetype=suntimetype)
        
        # 添加警告信息
        if warning_params:
            warning_msg = "\n\n⚠️ 注意：" + "；".join(warning_params)
            result["formatted_message"] += warning_msg
        
        return result
    else:
        return {
            "success": False,
            "message": f"请求失败: {data.get('msg', '未知错误')}"
        }


def query_domestic_weather(province: str, city: str, days: int = 1, day: int = None, suntimetype: int = None, dkey: str = None, uip: str = None) -> Dict[str, Any]:
    """查询中国境内指定省份和城市的天气
    
    Args:
        province: 省份名称
        city: 城市名称
        days: 查询天数，1-7，默认1
        day: 查询某一天的天气，1-7，None表示查询所有days天
        suntimetype: 是否返回7天日出日落详细时间，0=不返回，1=返回。默认0
        dkey: 动态秘钥（可选），用于客户端直接调用接口的场景
        uip: 用户IP（可选），用于后台统计IP地域分布、ISP运营商、时段IP数统计等
    
    Returns:
        天气查询结果字典
    """
    user_id, api_key = get_weather_api_config()
    
    # 使用统一的参数验证机制，强制hourtype为1
    params, warning_params, config_error = validate_parameters('domestic', days, day, 1, suntimetype, province, city)
    
    # 如果存在配置错误，返回错误
    if config_error:
        return {
            "success": False,
            "config_error": config_error
        }
    
    days = params['days']
    day = params['day']
    hourtype = 1
    suntimetype = params['suntimetype']
    province = params['province']
    city = params['city']
    
    url = f'https://cn.apihz.cn/api/tianqi/tqyb.php?id={user_id}&key={api_key}&sheng={province}&place={city}'
    
    # 总是查询最大天数（7天），以提高缓存命中率
    url += f'&day=7'
    # 强制hourtype为1，因为需要小时数据去计算最高最低温
    url += f'&hourtype=1'
    if suntimetype is not None:
        url += f'&suntimetype={suntimetype}'
    if dkey:
        url += f'&dkey={dkey}'
    if uip:
        url += f'&uip={uip}'
    
    response = requests.get(url)
    data = response.json()
    
    if data.get('code') == 200:
        location_info = f"{data.get('guo', '中国')} {data.get('sheng', '')} {data.get('shi', '')}"
        result = _format_weather_response(data, location_info, days=days, day=day, suntimetype=suntimetype)
        
        # 添加警告信息
        if warning_params:
            warning_msg = "\n\n⚠️ 注意：" + "；".join(warning_params)
            result["formatted_message"] += warning_msg
        
        return result
    else:
        return {
            "success": False,
            "message": f"请求失败: {data.get('msg', '未知错误')}"
        }


def query_foreign_weather(city: str, days: int = 1, day: int = None, dkey: str = None, uip: str = None) -> Dict[str, Any]:
    """查询国外主要城市的天气
    
    Args:
        city: 城市名称
        days: 查询天数，1-6，默认1
        day: 查询某一天的天气，1-6，None表示查询所有days天
        dkey: 动态秘钥（可选），用于客户端直接调用接口的场景
        uip: 用户IP（可选），用于后台统计IP地域分布、ISP运营商、时段IP数统计等
    
    Returns:
        天气查询结果字典
    """
    user_id, api_key = get_weather_api_config()
    
    # 使用统一的参数验证机制
    params, warning_params, config_error = validate_parameters('foreign', days, day, None, None, None, city)
    
    # 如果存在配置错误，返回错误
    if config_error:
        return {
            "success": False,
            "config_error": config_error
        }
    
    days = params['days']
    day = params['day']
    city = params['city']
    
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
                # 根据API文档，国外天气API返回的字段可能与国内不同
                forecast_list.append({
                    "date": day_data.get('date', ''),
                    "date_formatted": day_data.get('date', '') or day_data.get('monthDay', ''),
                    "weekday": day_data.get('weekday', ''),
                    "weekday_cn": day_data.get('weekday', ''),
                    "day_weather": day_data.get('weather1', ''),
                    "night_weather": day_data.get('weather2', ''),
                    "day_weather_img": day_data.get('weather1img', ''),  # 国外天气API也提供天气图标
                    "night_weather_img": day_data.get('weather2img', ''),  # 国外天气API也提供天气图标
                    "day_temp_high": day_data.get('wd1', ''),
                    "night_temp_low": day_data.get('wd2', ''),
                    "wind_direction": day_data.get('winddirection1', '') or day_data.get('winddirection', ''),
                    "wind_scale": day_data.get('windleve1', '') or day_data.get('windleve', '')
                })
        
        print(f"forecast_list长度: {len(forecast_list)}")
        print(f"forecast_list内容: {forecast_list}")
        
        if forecast_list:
            # 根据day参数决定显示哪些天的天气
            if day is not None:
                # 只显示指定天的天气
                if forecast_list and day <= len(forecast_list):
                    day_data = forecast_list[day - 1]
                    date_display = day_data.get('date_formatted', '')
                    # 确保日期显示不为空
                    if not date_display:
                        if day == 1:
                            date_display = "今天"
                        elif day == 2:
                            date_display = "明天"
                        else:
                            date_display = f"{day-1}天后"
                    formatted_message += f"{date_display}: {day_data['day_weather']}转{day_data['night_weather']}, {day_data['day_temp_high']}℃/{day_data['night_temp_low']}℃"
                    if day_data['wind_direction'] or day_data['wind_scale']:
                        formatted_message += f", {day_data['wind_direction']} {day_data['wind_scale']}"
                    formatted_message += "\n"
                
                    result = {
                        "success": True,
                        "formatted_message": formatted_message,
                        "location": {
                            "country": data.get('guo', ''),
                            "city": data.get('city', '')
                        },
                        "day": day,
                        "day_weather": day_data,
                        "weather_images": {
                            "day": day_data.get('day_weather_img'),
                            "night": day_data.get('night_weather_img')
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"查询的day参数{day}超出范围，最大支持{len(forecast_list)}天"
                    }
            else:
                # 显示指定天数的天气
                if days > 1:
                    formatted_message += "未来几天预报:\n"
                
                for i in range(min(days, len(forecast_list))):
                    day_data = forecast_list[i]
                    date_display = day_data.get('date_formatted', '')
                    # 确保日期显示不为空
                    if not date_display:
                        if i == 0:
                            date_display = "今天"
                        elif i == 1:
                            date_display = "明天"
                        else:
                            date_display = f"{i}天后"
                    formatted_message += f"• {date_display}: {day_data['day_weather']}转{day_data['night_weather']}, {day_data['day_temp_high']}℃/{day_data['night_temp_low']}℃"
                    if day_data['wind_direction'] or day_data['wind_scale']:
                        formatted_message += f", {day_data['wind_direction']} {day_data['wind_scale']}"
                    formatted_message += "\n"
                
                result = {
                    "success": True,
                    "formatted_message": formatted_message,
                    "location": {
                        "country": data.get('guo', ''),
                        "city": data.get('city', '')
                    },
                    "days": days,
                    "forecast": forecast_list[:days],
                    "weather_images": {
                        "today": forecast_list[0].get('day_weather_img') if forecast_list else None,
                        "today_night": forecast_list[0].get('night_weather_img') if forecast_list else None,
                        "tomorrow": forecast_list[1].get('day_weather_img') if len(forecast_list) > 1 else None,
                        "tomorrow_night": forecast_list[1].get('night_weather_img') if len(forecast_list) > 1 else None
                    }
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
    async def weather_query(
        operation: WeatherOperationEnum,
        province: str = None,
        city: str = None,
        ip: str = None,
        days: int = 1,
        day: int = None,
        suntimetype: int = None,
        dkey: str = None,
        uip: str = None
    ) -> Dict[str, Any]:
        """天气查询工具
        
        用于查询天气信息，包括实时天气、7天预报、小时预报、日出日落时间和气象预警等。
        # 天气查询工具
        # 支持的操作类型：
        #   - "ip_weather": 根据当前IP地址查询天气（忽略city参数）
        #   - "domestic_weather": 查询中国国内城市天气（必需province和city参数）
        #   - "foreign_weather": 查询中国以外城市天气（必需city参数）

        Args:
            operation: 操作类型
            province: 省份名称（仅domestic_weather需要，必填参数），例如："北京"、"上海"、"广东"、"湖南"
            city: 城市名称（domestic_weather和foreign_weather需要），例如："朝阳"、"浦东"、"深圳"、"东京"、"纽约"
            ip: IP地址（仅ip_weather），要查询的ip地址，如不传则自动获取当前公网IP地址
            days: 查询天数（ip_weather和domestic_weather），1-7，默认1
            day: 查询某一天的天气（ip_weather和domestic_weather），1-7(None表示查询所有days天，配合days参数使用；当day参数被指定时，会忽略days参数的值）。今天为1，明天为2，以此类推。
            suntimetype: 是否返回7天日出日落详细时间（ip_weather和domestic_weather），0=不返回，1=返回。默认0
        
        Returns:
            {
                "success": True/False,
                "formatted_message": "格式化的自然语言描述",
                "location": {...},
                "current": {...},
                "day_night": {...},
                "forecast": [...],
                "hourly": [...],
                "sunrise_sunset": [...],
                "alarm": "...",
                "message": "错误信息（如果失败）"
            }

        注意：
            - 如果是中国国内城市天气查询，必须根据提供的中国国内城市自动补全省份。例如："长春市天气" -> province="吉林", city="长春"

        Examples:
            - 查询今天天气: weather_query("ip_weather")
            - 哈尔滨市未来第x天日出日落时间: weather_query("domestic_weather", province="黑龙江", city="哈尔滨", day=x, suntimetype=1)
            - 查询伦敦未来x天天气，包含日出日落: weather_query("foreign_weather", city="伦敦", day=None, days=x, suntimetype=1)
        """
        try:
            print(f"weather_query被调用，参数: operation={operation}, province={province}, city={city}, ip={ip}, days={days}, day={day}, suntimetype={suntimetype}")
            
            if operation == "ip_weather":
                return query_ip_weather(ip, days, day, suntimetype, dkey, uip)
            elif operation == "domestic_weather":
                return query_domestic_weather(province, city, days, day, suntimetype, dkey, uip)
            elif operation == "foreign_weather":
                return query_foreign_weather(city, days, day, dkey, uip)
            else:
                # 返回包含config_error的字典
                return {
                    "success": False,
                    "config_error": f"不支持的操作类型: {operation}，支持的类型: ip_weather, domestic_weather, foreign_weather"
                }
                
        except ValueError as e:
            # 重新抛出ValueError异常，触发自动修复机制
            raise
        except Exception as e:
            # 其他异常作为正常执行失败，返回错误字典
            print(f"weather_query执行出错: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"程序执行出错: {str(e)}"
            }

