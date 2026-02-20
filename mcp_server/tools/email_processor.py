# 邮件处理工具

import os
import smtplib
import imaplib
import email
import socket
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from mcp.server.fastmcp import Context

# 从file_operations导入process_path函数
from mcp_server.tools.file_operations import process_path

# 从config导入配置
from user_config.config import get_config


def register_email_processor_tools(mcp, security_checker=None, output_callback=None):
    """注册邮件处理工具到MCP服务器
    
    Args:
        mcp: FastMCP实例
        security_checker: 安全检查器（可选）
        output_callback: 输出回调函数（可选）
    """
    
    @mcp.tool()
    async def email_processor(
        operation: str,
        recipient: str,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        attachments: Optional[str] = None,
        imap_server: Optional[str] = None,
        imap_port: Optional[int] = None,
        ctx: Optional[Context] = None
    ) -> Dict[str, Any]:
        """邮件处理工具
        
        支持发送邮件（含附件）和接收邮件功能。
        
        Args:
            operation: 操作类型，可选值：
                - "send": 发送邮件
                - "receive": 接收邮件
            recipient: 收件人邮箱地址（用于发送邮件）或发件人邮箱地址（用于接收邮件）
            smtp_server: SMTP服务器地址（用于发送邮件，默认从配置文件读取）
            smtp_port: SMTP服务器端口（用于发送邮件，默认从配置文件读取）
            smtp_username: SMTP用户名（用于发送邮件，默认从配置文件读取）
            smtp_password: SMTP密码（用于发送邮件，默认从配置文件读取）
            subject: 邮件主题（用于发送邮件）
            body: 邮件正文（用于发送邮件）
            attachments: 附件路径（用于发送邮件，多个附件用分号分隔）
            imap_server: IMAP服务器地址（用于接收邮件，默认从配置文件读取）
            imap_port: IMAP服务器端口（用于接收邮件，默认从配置文件读取）
            ctx: FastMCP上下文，用于elicitation（可选）
        
        Returns:
            {
                "success": True/False,
                "result": 操作结果描述,
                "error": 错误信息（如果失败）
            }
        
        Examples:
            - 发送邮件: email_processor("send", "recipient@example.com", subject="测试邮件", body="这是一封测试邮件")
            - 发送带附件的邮件: email_processor("send", "recipient@example.com", subject="测试邮件", body="这是一封带附件的测试邮件", attachments="文件1.pdf;文件2.docx")
            - 接收邮件: email_processor("receive", "sender@example.com")
        """
        try:
            # 验证邮箱地址格式
            def validate_email(email_address: str) -> bool:
                """验证邮箱地址格式是否正确"""
                pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return bool(re.match(pattern, email_address))
            
            # 验证收件人邮箱地址格式
            if not validate_email(recipient):
                return {
                    "success": False, 
                    "error": f"收件人邮箱地址格式不正确: {recipient}",
                    "formatted_message": f"❌ 错误: 收件人邮箱地址格式不正确\n📧 邮箱: {recipient}"
                }
            
            # 优先从环境变量读取，然后从配置文件读取，最后使用默认值
            smtp_server = smtp_server or os.getenv('SMTP_SERVER', '') or get_config("email.smtp.server", "smtp.example.com")
            
            # 根据SMTP服务器域名确定邮箱服务商
            email_provider = "unknown"
            if "163.com" in smtp_server:
                email_provider = "163"
            elif "qq.com" in smtp_server:
                email_provider = "qq"
            
            # 优先从环境变量读取SMTP端口，然后从配置文件读取，最后使用默认值
            try:
                smtp_port = smtp_port or int(os.getenv('SMTP_PORT', '')) if os.getenv('SMTP_PORT', '') else None
            except ValueError:
                smtp_port = None
            smtp_port = smtp_port or get_config("email.smtp.port", 465)
            
            # 根据邮箱服务商从环境变量读取SMTP用户名和密码，然后从配置文件读取
            if email_provider == "163":
                smtp_username = smtp_username or os.getenv('SMTP_163_USERNAME', '') or os.getenv('SMTP_USERNAME', '') or get_config("email.smtp.username", "")
                smtp_password = smtp_password or os.getenv('SMTP_163_PASSWORD', '') or os.getenv('SMTP_PASSWORD', '') or get_config("email.smtp.password", "")
            elif email_provider == "qq":
                smtp_username = smtp_username or os.getenv('SMTP_QQ_USERNAME', '') or os.getenv('SMTP_USERNAME', '') or get_config("email.smtp.username", "")
                smtp_password = smtp_password or os.getenv('SMTP_QQ_PASSWORD', '') or os.getenv('SMTP_PASSWORD', '') or get_config("email.smtp.password", "")
            else:
                smtp_username = smtp_username or os.getenv('SMTP_USERNAME', '') or get_config("email.smtp.username", "")
                smtp_password = smtp_password or os.getenv('SMTP_PASSWORD', '') or get_config("email.smtp.password", "")
            
            # 优先从环境变量读取IMAP服务器，然后从配置文件读取
            imap_server = imap_server or os.getenv('IMAP_SERVER', '') or get_config("email.imap.server", "")
            
            # 优先从环境变量读取IMAP端口，然后从配置文件读取，最后使用默认值
            try:
                imap_port = imap_port or int(os.getenv('IMAP_PORT', '')) if os.getenv('IMAP_PORT', '') else None
            except ValueError:
                imap_port = None
            imap_port = imap_port or get_config("email.imap.port", 993)
            
            # 验证必要参数
            if operation == "send":
                if not smtp_username:
                    return {
                        "success": False, 
                        "error": "缺少SMTP用户名，请在配置文件中设置或直接提供",
                        "formatted_message": "❌ 错误: 缺少SMTP用户名，请在配置文件中设置或直接提供"
                    }
                if not smtp_password:
                    return {
                        "success": False, 
                        "error": "缺少SMTP密码，请在配置文件中设置或直接提供",
                        "formatted_message": "❌ 错误: 缺少SMTP密码，请在配置文件中设置或直接提供"
                    }
            elif operation == "receive":
                if not smtp_username:
                    return {
                        "success": False, 
                        "error": "缺少邮箱用户名，请在配置文件中设置或直接提供",
                        "formatted_message": "❌ 错误: 缺少邮箱用户名，请在配置文件中设置或直接提供"
                    }
                if not smtp_password:
                    return {
                        "success": False, 
                        "error": "缺少邮箱密码，请在配置文件中设置或直接提供",
                        "formatted_message": "❌ 错误: 缺少邮箱密码，请在配置文件中设置或直接提供"
                    }
            if operation == "send":
                # 发送邮件
                try:
                    # 创建邮件
                    msg = MIMEMultipart()
                    msg['From'] = smtp_username
                    msg['To'] = recipient
                    msg['Subject'] = subject or ""
                    
                    # 添加邮件正文
                    msg.attach(MIMEText(body or "", 'plain', 'utf-8'))
                    
                    # 添加附件
                    attachment_count = 0
                    if attachments:
                        attachment_paths = [p.strip() for p in attachments.split(";" if ";" in attachments else ",")]
                        for attachment_path in attachment_paths:
                            if attachment_path:
                                # 处理附件路径
                                processed_path = process_path(attachment_path)
                                
                                # 检查文件是否存在
                                if not os.path.exists(processed_path):
                                    return {
                                        "success": False, 
                                        "error": f"附件文件不存在: {processed_path}",
                                        "formatted_message": f"❌ 错误: 附件文件不存在\n📄 文件: {os.path.basename(processed_path)}\n📍 路径: {processed_path}"
                                    }
                                attachment_count += 1
                                # 读取附件文件
                                with open(processed_path, 'rb') as f:
                                    part = MIMEApplication(f.read())
                                    part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(processed_path))
                                    msg.attach(part)
                    
                    # 连接SMTP服务器并发送邮件
                    try:
                        # 根据邮箱服务商选择正确的连接方式
                        if email_provider == "163":
                            # 163邮箱使用SMTP_SSL和465端口
                            server = smtplib.SMTP_SSL(smtp_server, 465, timeout=30)
                        else:
                            # 其他邮箱根据端口选择连接方式
                            if smtp_port == 465:
                                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
                            else:
                                server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                                server.starttls()
                        
                        # 设置调试模式，捕获详细的SMTP通信信息
                        server.set_debuglevel(2)
                        
                        # 登录并发送邮件
                        server.login(smtp_username, smtp_password)
                        server.sendmail(smtp_username, recipient, msg.as_string())
                        server.quit()
                    finally:
                        # 确保服务器连接被关闭
                        try:
                            server.quit()
                        except:
                            pass
                    
                    return {
                        "success": True, 
                        "result": f"邮件发送成功，收件人: {recipient}",
                        "formatted_message": f"✅ 邮件发送成功\n📧 收件人: {recipient}\n📤 发件人: {smtp_username}\n📝 主题: {subject or '无'}\n📎 附件数: {attachment_count}\n🌐 服务器: {smtp_server}:{smtp_port}"
                    }
                except socket.gaierror as e:
                    # DNS 解析错误
                    return {
                        "success": False, 
                        "error": f"DNS 解析错误: {str(e)} - 请检查 SMTP 服务器地址是否正确: {smtp_server}",
                        "formatted_message": f"❌ DNS 解析错误\n🌐 服务器: {smtp_server}\n💬 错误: {str(e)}"
                    }
                except socket.timeout as e:
                    # 连接超时错误
                    return {
                        "success": False, 
                        "error": f"连接超时错误: {str(e)} - 请检查网络连接和防火墙设置，确保能访问 SMTP 服务器: {smtp_server}:{smtp_port}",
                        "formatted_message": f"❌ 连接超时错误\n🌐 服务器: {smtp_server}:{smtp_port}\n💬 错误: {str(e)}"
                    }
                except smtplib.SMTPAuthenticationError:
                    # 认证错误
                    return {
                        "success": False, 
                        "error": "SMTP 认证失败 - 请检查用户名和密码是否正确",
                        "formatted_message": "❌ SMTP 认证失败\n💡 请检查用户名和密码是否正确"
                    }
                except smtplib.SMTPConnectError as e:
                    # 连接错误
                    return {
                        "success": False, 
                        "error": f"SMTP 连接失败: {str(e)} - 请检查网络连接和服务器地址",
                        "formatted_message": f"❌ SMTP 连接失败\n🌐 服务器: {smtp_server}:{smtp_port}\n💬 错误: {str(e)}"
                    }
                except Exception as e:
                    # 其他错误
                    return {
                        "success": False, 
                        "error": f"发送邮件失败: {str(e)}",
                        "formatted_message": f"❌ 发送邮件失败\n💬 错误: {str(e)}"
                    }
            
            elif operation == "receive":
                # 接收邮件
                try:
                    if not imap_server or not imap_port:
                        return {
                            "success": False, 
                            "error": "接收邮件需要提供IMAP服务器地址和端口",
                            "formatted_message": "❌ 错误: 接收邮件需要提供IMAP服务器地址和端口"
                        }
                    
                    # 连接IMAP服务器
                    with imaplib.IMAP4_SSL(imap_server, imap_port) as server:
                        server.login(smtp_username, smtp_password)
                        server.select('INBOX')
                        
                        # 搜索来自指定发件人的邮件
                        status, messages = server.search(None, f'FROM "{recipient}"')
                        
                        if status != 'OK':
                            return {
                                "success": False, 
                                "error": "搜索邮件失败",
                                "formatted_message": "❌ 搜索邮件失败"
                            }
                        
                        # 获取邮件ID列表
                        email_ids = messages[0].split()
                        
                        # 限制获取的邮件数量
                        email_ids = email_ids[-10:]  # 只获取最新的10封邮件
                        
                        # 解析邮件
                        received_emails = []
                        for email_id in email_ids:
                            status, msg_data = server.fetch(email_id, '(RFC822)')
                            if status != 'OK':
                                continue
                            
                            for response_part in msg_data:
                                if isinstance(response_part, tuple):
                                    msg = email.message_from_bytes(response_part[1])
                                    
                                    # 提取邮件信息
                                    email_info = {
                                        "from": msg.get('From'),
                                        "to": msg.get('To'),
                                        "subject": msg.get('Subject'),
                                        "date": msg.get('Date'),
                                        "body": ""
                                    }
                                    
                                    # 提取邮件正文
                                    if msg.is_multipart():
                                        for part in msg.walk():
                                            if part.get_content_type() == 'text/plain' and not part.get('Content-Disposition'):
                                                email_info["body"] = part.get_payload(decode=True).decode('utf-8', errors='replace')
                                                break
                                    else:
                                        if msg.get_content_type() == 'text/plain':
                                            email_info["body"] = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                                    
                                    received_emails.append(email_info)
                        
                        # 构建formatted_message
                        formatted_msg = f"✅ 成功接收 {len(received_emails)} 封邮件\n📧 发件人: {recipient}\n📥 收件箱: {smtp_username}"
                        if received_emails:
                            formatted_msg += "\n\n📋 邮件列表:"
                            for i, email_info in enumerate(received_emails[:3], 1):  # 只显示前3封
                                formatted_msg += f"\n\n{i}. 主题: {email_info['subject'] or '无'}"
                                formatted_msg += f"\n   日期: {email_info['date'] or '未知'}"
                                formatted_msg += f"\n   发件人: {email_info['from'] or '未知'}"
                                if len(email_info['body']) > 100:
                                    formatted_msg += f"\n   正文: {email_info['body'][:100]}..."
                                else:
                                    formatted_msg += f"\n   正文: {email_info['body'] or '无'}"
                            if len(received_emails) > 3:
                                formatted_msg += f"\n\n... 还有 {len(received_emails) - 3} 封邮件未显示"
                        
                        return {
                            "success": True, 
                            "result": f"成功接收 {len(received_emails)} 封邮件", 
                            "emails": received_emails,
                            "formatted_message": formatted_msg
                        }
                except Exception as e:
                    return {
                        "success": False, 
                        "error": f"接收邮件失败: {str(e)}",
                        "formatted_message": f"❌ 接收邮件失败\n💬 错误: {str(e)}"
                    }
            
            else:
                return {
                    "success": False, 
                    "error": f"不支持的操作: {operation}",
                    "formatted_message": f"❌ 错误: 不支持的操作 '{operation}'"
                }
        
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "formatted_message": f"❌ 错误: {str(e)}"
            }