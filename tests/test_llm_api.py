"""测试后端大纲生成API和LLM连接"""
import json
import time
from pathlib import Path
import litellm
import asyncio

# 读取配置
config_path = Path('workspace/.config.json')
cfg = json.loads(config_path.read_text(encoding='utf-8'))
print('当前LLM配置:')
print(json.dumps(cfg.get('llm', {}), indent=2, ensure_ascii=False))

async def test_llm():
    llm_cfg = cfg.get('llm', {})
    model = llm_cfg.get('model', 'deepseek-chat')
    api_type = llm_cfg.get('apiType', 'deepseek')
    
    if api_type == 'deepseek' and not model.startswith('deepseek/'):
        model = 'deepseek/' + model
    
    print(f'\n调用模型: {model}')
    api_key = llm_cfg.get('apiKey', '')
    print(f'API Key: {api_key[:20]}...' if api_key else 'API Key: (空)')
    print(f'API URL: {llm_cfg.get("apiUrl", "")}')
    
    try:
        start = time.time()
        response = await litellm.acompletion(
            model=model,
            messages=[{'role': 'user', 'content': '请用一句话回答：你好'}],
            temperature=0.7,
            max_tokens=100,
            api_key=api_key,
            api_base=llm_cfg.get('apiUrl'),
        )
        elapsed = time.time() - start
        print(f'\nLLM响应成功 (耗时{elapsed:.1f}s): {response.choices[0].message.content}')
        return True
    except Exception as e:
        print(f'\nLLM调用失败: {type(e).__name__}: {e}')
        return False

async def test_outline_api():
    """测试大纲生成API"""
    import requests
    
    print('\n=== 测试大纲生成API ===')
    start = time.time()
    try:
        r = requests.post(
            'http://127.0.0.1:8000/api/wizard/test-proj/generate-outline',
            json={
                'genre': '玄幻',
                'tone': '热血',
                'theme': '',
                'writing_style': '快节奏',
                'target_word_count': 100000,
                'book_name': '测试书名',
                'book_description': '这是一个测试描述'
            },
            timeout=120
        )
        elapsed = time.time() - start
        print(f'状态码: {r.status_code}')
        print(f'耗时: {elapsed:.1f}s')
        
        result = r.json()
        if result.get('success'):
            outline = result['data']['outline']
            print(f'大纲内容长度: {len(outline)} 字符')
            print(f'大纲预览: {outline[:300]}')
            
            if '待生成' in outline:
                print('\n警告: 大纲返回的是占位内容，说明LLM调用可能失败了')
            else:
                print('\n成功: 大纲包含实际内容')
        else:
            print(f'错误: {result.get("error")}')
    except requests.exceptions.Timeout:
        print(f'请求超时 (>{120}s)')
    except Exception as e:
        print(f'错误: {type(e).__name__}: {e}')

async def main():
    llm_ok = await test_llm()
    if llm_ok:
        await test_outline_api()
    else:
        print('\nLLM调用失败，跳过API测试')

asyncio.run(main())
