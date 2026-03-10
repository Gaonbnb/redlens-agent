import requests
import json
import time

# ================= 配置区域 =================
# 1. 替换为你在智谱控制台创建的 API Key (格式: xxxxxxxx.xxxxxxxxxx)
API_KEY = "79c5bcbc3ace4dfbb5d05ac0566feb41.3lSem7pEwktBdEnG"

# 2. 智谱 API 地址 (兼容 OpenAI v4 格式)
API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# 3. 模型名称 (glm-4-flash 目前免费且速度快)
MODEL_NAME = "glm-4-flash"
# ===========================================

def call_zhipu_api(user_prompt):
    # 构造请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    # 构造请求体 (完全符合 OpenAI 标准格式)
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "你是一个智能助手，回答要简洁准确。"},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,  # 设置为 False 以便一次性获取完整结果
        "temperature": 0.7
    }

    print(f"🚀 正在向智谱 ({MODEL_NAME}) 发送请求...")
    
    try:
        # 发送 POST 请求
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        # 检查状态码
        if response.status_code == 200:
            data = response.json()
            # 解析返回结果
            content = data['choices'][0]['message']['content']
            usage = data.get('usage', {})
            
            return {
                "success": True,
                "content": content,
                "tokens_used": usage.get('total_tokens', 0)
            }
        else:
            # 处理错误 (如 Key 错误、额度不足、限流等)
            error_msg = response.json().get('error', {}).get('message', '未知错误')
            return {
                "success": False,
                "error_code": response.status_code,
                "error_msg": error_msg
            }

    except requests.exceptions.Timeout:
        return {"success": False, "error_msg": "请求超时，请检查网络"}
    except Exception as e:
        return {"success": False, "error_msg": str(e)}

# ================= 主程序 =================
if __name__ == "__main__":
    # 测试问题
    question = "请用 Python 写一个快速排序算法，并简要解释原理。"
    
    # 调用函数
    result = call_zhipu_api(question)
    
    # 输出结果
    if result["success"]:
        print("\n✅ 获取成功！")
        print("-" * 30)
        print(result["content"])
        print("-" * 30)
        print(f"💰 消耗 Token 数: {result['tokens_used']}")
    else:
        print("\n❌ 调用失败！")
        print(f"错误代码: {result.get('error_code', 'N/A')}")
        print(f"错误信息: {result['error_msg']}")
        
        # 常见错误提示
        if "invalid_api_key" in str(result.get('error_msg', '')).lower():
            print("💡 提示：请检查 API_KEY 是否复制正确（包含中间的点）。")
        elif "quota" in str(result.get('error_msg', '')).lower():
            print("💡 提示：免费额度可能已用完，请明天再试或充值。")