import requests
from typing import Optional, Dict, Any

def http_request(
    method: str,
    url: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 10,
) -> Dict[str, Any]:
    """
    通用的HTTP请求工具方法，支持GET/POST请求

    Args:
        method: 请求方法，支持'GET'/'POST'（大小写不敏感）
        url: 请求的URL地址
        params: URL查询参数（GET请求专用），默认为None
        data: POST表单数据（application/x-www-form-urlencoded），默认为None
        json: POST JSON数据（application/json），默认为None
        headers: 请求头，默认为None
        timeout: 请求超时时间（秒），默认为10秒

    Returns:
        字典格式的响应结果，包含：
        - success: 布尔值，请求是否成功
        - status_code: HTTP状态码（成功时返回，失败时为None）
        - response: 响应内容（JSON/文本，成功时返回，失败时为None）
        - error: 错误信息（失败时返回，成功时为None）
    """
    # 初始化返回结果
    result = {"success": False, "status_code": None,
              "response": None, "error": None}
    if headers is None:
        headers = {}
    if headers.get("User-Agent") is None:
        headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        )
    # 统一请求方法为大写
    method = method.upper()

    # 校验请求方法是否支持
    if method not in ["GET", "POST"]:
        result["error"] = f"不支持的请求方法：{method}，仅支持GET/POST"
        return result

    try:
        # 根据请求方法发送请求
        if method == "GET":
            response = requests.get(
                url=url, params=params, headers=headers, timeout=timeout
            )
        elif method == "POST":
            response = requests.post(
                url=url,
                params=params,  # POST也支持URL参数
                data=data,
                json=json,
                headers=headers,
                timeout=timeout,
            )

        # 检查HTTP状态码，4xx/5xx会抛出异常
        response.raise_for_status()

        # 尝试解析JSON响应，失败则返回文本
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text

        # 更新成功的返回结果
        result["success"] = True
        result["status_code"] = response.status_code
        result["response"] = response_data

    except requests.exceptions.Timeout:
        result["error"] = f"请求超时（超时时间：{timeout}秒）"
    except requests.exceptions.ConnectionError:
        result["error"] = "网络连接错误（无法连接到服务器）"
    except requests.exceptions.HTTPError as e:
        result["error"] = f"HTTP请求错误：{str(e)}"
        result["status_code"] = response.status_code if "response" in locals() else None
    except Exception as e:
        result["error"] = f"未知错误：{str(e)}"

    return result
