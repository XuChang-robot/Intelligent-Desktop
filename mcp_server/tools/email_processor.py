# 邮件处理工具

import os
import smtplib
import imaplib
import email
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from mcp.server.fastmcp import Context

# 从file_operations导入process_path函数
from mcp_server.tools.file_operations import process_path

# 从config导入配置
from config.config import get_config


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
            # 从配置文件读取默认值
            smtp_server = smtp_server or get_config("email.smtp.server", "smtp.example.com")
            # 优先从环境变量读取SMTP端口
            try:
                smtp_port = smtp_port or (int(os.getenv('SMTP_PORT', '')) if os.getenv('SMTP_PORT', '') else None) or get_config("email.smtp.port", 587)
            except ValueError:
                smtp_port = smtp_port or get_config("email.smtp.port", 587)
            
            # 优先从环境变量读取SMTP用户名和密码
            smtp_username = smtp_username or os.getenv('SMTP_USERNAME', '') or get_config("email.smtp.username", "")
            smtp_password = smtp_password or os.getenv('SMTP_PASSWORD', '') or get_config("email.smtp.password", "")
            
            imap_server = imap_server or get_config("email.imap.server", "")
            # 优先从环境变量读取IMAP端口
            try:
                imap_port = imap_port or (int(os.getenv('IMAP_PORT', '')) if os.getenv('IMAP_PORT', '') else None) or get_config("email.imap.port", 993)
            except ValueError:
                imap_port = imap_port or get_config("email.imap.port", 993)
            
            # 验证必要参数
            if operation == "send":
                if not smtp_username:
                    return {"success": False, "error": "缺少SMTP用户名，请在配置文件中设置或直接提供"}
                if not smtp_password:
                    return {"success": False, "error": "缺少SMTP密码，请在配置文件中设置或直接提供"}
            elif operation == "receive":
                if not smtp_username:
                    return {"success": False, "error": "缺少邮箱用户名，请在配置文件中设置或直接提供"}
                if not smtp_password:
                    return {"success": False, "error": "缺少邮箱密码，请在配置文件中设置或直接提供"}
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
                    if attachments:
                        attachment_paths = [p.strip() for p in attachments.split(";" if ";" in attachments else ",")]
                        for attachment_path in attachment_paths:
                            if attachment_path:
                                # 处理附件路径
                                processed_path = process_path(attachment_path)
                                
                                # 检查文件是否存在
                                if not os.path.exists(processed_path):
                                    return {"success": False, "error": f"附件文件不存在: {processed_path}"}
                                
                                # 读取附件文件
                                with open(processed_path, 'rb') as f:
                                    part = MIMEApplication(f.read())
                                    part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(processed_path))
                                    msg.attach(part)
                    
                    # 连接SMTP服务器并发送邮件
                    with smtplib.SMTP(smtp_server, smtp_port) as server:
                        server.starttls()
                        server.login(smtp_username, smtp_password)
                        server.send_message(msg)
                    
                    return {"success": True, "result": f"邮件发送成功，收件人: {recipient}"}
                except socket.gaierror as e:
                    # DNS 解析错误
                    return {"success": False, "error": f"DNS 解析错误: {str(e)} - 请检查 SMTP 服务器地址是否正确: {smtp_server}"}
                except smtplib.SMTPAuthenticationError:
                    # 认证错误
                    return {"success": False, "error": "SMTP 认证失败 - 请检查用户名和密码是否正确"}
                except smtplib.SMTPConnectError as e:
                    # 连接错误
                    return {"success": False, "error": f"SMTP 连接失败: {str(e)} - 请检查网络连接和服务器地址"}
                except Exception as e:
                    # 其他错误
                    return {"success": False, "error": f"发送邮件失败: {str(e)}"}
            
            elif operation == "receive":
                # 接收邮件
                try:
                    if not imap_server or not imap_port:
                        return {"success": False, "error": "接收邮件需要提供IMAP服务器地址和端口"}
                    
                    # 连接IMAP服务器
                    with imaplib.IMAP4_SSL(imap_server, imap_port) as server:
                        server.login(smtp_username, smtp_password)
                        server.select('INBOX')
                        
                        # 搜索来自指定发件人的邮件
                        status, messages = server.search(None, f'FROM "{recipient}"')
                        
                        if status != 'OK':
                            return {"success": False, "error": "搜索邮件失败"}
                        
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
                        
                        return {"success": True, "result": f"成功接收 {len(received_emails)} 封邮件", "emails": received_emails}
                except Exception as e:
                    return {"success": False, "error": f"接收邮件失败: {str(e)}"}
            
            else:
                return {"success": False, "error": f"不支持的操作: {operation}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}