import requests
import json
import hashlib
import os
import re

def main():
    # 记录执行前状态
    print('=== 执行前状态 ===')
    
    target_file = 'workspace/projects/demo-novel/chapters/vol-01/ch-001/sec-001.md'
    with open(target_file, 'rb') as f:
        md5_before = hashlib.md5(f.read()).hexdigest()
    print(f'Target file MD5 (before): {md5_before}')
    print(f'Target file mtime (before): {os.path.getmtime(target_file)}')

    candidates_dir = 'workspace/projects/demo-novel/.candidates'
    candidate_files_before = [f for f in os.listdir(candidates_dir) if f.endswith('.json') and f != 'metadata.json']
    candidate_count_before = len(candidate_files_before)
    print(f'Candidate count (before): {candidate_count_before}')
    
    # 调用 Professional dry-run
    url = 'http://localhost:8080/api/pipeline/run'
    data = {
        'pipeline': 'polish',
        'project_id': 'demo-novel',
        'target_file': 'chapters/vol-01/ch-001/sec-001.md',
        'output_mode': 'candidate',
        'extra_vars': {},
        'scene_plan': {
            'project_id': 'demo-novel',
            'source_path': 'chapters/vol-01/ch-001/sec-001.md',
            'title': '测试场景计划',
            'goal': '测试场景目标',
            'conflict': '测试冲突',
            'required_beats': ['beat1', 'beat2', 'beat3'],
            'characters': ['测试角色'],
            'output_intent': 'polish',
            'candidate_policy': {'allow_direct_write': False, 'require_candidate': True},
            'metadata': {'created_by': 'human'}
        }
    }

    print('\n=== 调用 Professional dry-run ===')
    print('请求体包含 scene_plan:', 'scene_plan' in data)
    print('scene_plan.source_path:', data['scene_plan']['source_path'])
    print('target_file:', data['target_file'])
    print('source_path == target_file:', data['scene_plan']['source_path'] == data['target_file'])

    response = requests.post(url, json=data, stream=True)
    print(f'HTTP 状态码: {response.status_code}')

    # 解析 SSE 响应
    print('\n=== SSE 响应 ===')
    candidate_created = False
    candidate_id = None
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            print(decoded_line[:200])
            if 'candidate_created' in decoded_line:
                candidate_created = True
                match = re.search(r'candidate_id.*?:.*?["\'](.*?)["\']', decoded_line)
                if match:
                    candidate_id = match.group(1)

    print(f'\n=== 执行后验证 ===')
    with open(target_file, 'rb') as f:
        md5_after = hashlib.md5(f.read()).hexdigest()
    print(f'Target file MD5 (after): {md5_after}')
    print(f'MD5 保持不变: {md5_before == md5_after}')

    candidate_files_after = [f for f in os.listdir(candidates_dir) if f.endswith('.json') and f != 'metadata.json']
    candidate_count_after = len(candidate_files_after)
    print(f'Candidate count (after): {candidate_count_after}')
    print(f'Candidate 数量增加: {candidate_count_after > candidate_count_before}')
    print(f'Candidate created: {candidate_created}')
    print(f'新 candidate_id: {candidate_id}')
    
    # 检查新 candidate
    new_candidates = set(candidate_files_after) - set(candidate_files_before)
    if new_candidates:
        new_candidate_file = list(new_candidates)[0]
        candidate_path = os.path.join(candidates_dir, new_candidate_file)
        with open(candidate_path, 'r', encoding='utf-8') as f:
            candidate_data = json.load(f)
        print(f'\n=== 新 candidate 内容 ===')
        print(f'Candidate ID: {candidate_data.get("id")}')
        print(f'Source: {candidate_data.get("source")}')
        content = candidate_data.get('content', '')
        print(f'内容长度: {len(content)} 字符')
        print(f'内容预览: {content[:300]}...')
        
    # 负向验证：不勾选时请求不包含 scene_plan
    print('\n=== 负向验证：不包含 scene_plan ===')
    data_no_plan = {
        'pipeline': 'polish',
        'project_id': 'demo-novel',
        'target_file': 'chapters/vol-01/ch-001/sec-001.md',
        'output_mode': 'candidate',
        'extra_vars': {}
    }
    
    response_no_plan = requests.post(url, json=data_no_plan, stream=True)
    print(f'HTTP 状态码: {response_no_plan.status_code}')
    print('请求体不包含 scene_plan:', 'scene_plan' not in data_no_plan)
    
    return {
        'md5_unchanged': md5_before == md5_after,
        'candidate_created': candidate_created,
        'candidate_count_increased': candidate_count_after > candidate_count_before,
        'request_had_scene_plan': 'scene_plan' in data,
        'negative_test_ok': 'scene_plan' not in data_no_plan
    }

if __name__ == '__main__':
    result = main()
    print('\n=== 测试结果 ===')
    all_pass = all(result.values())
    print(f'全部通过: {all_pass}')
    exit(0 if all_pass else 1)