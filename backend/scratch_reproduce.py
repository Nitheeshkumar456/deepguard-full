import urllib.request, urllib.error, json, os
from app.database import SessionLocal
from app.models.auth import User
from app.utils.auth_utils import create_access_token

db = SessionLocal()
user = db.query(User).filter(User.email == 'tester@deepguard.ai').first()
if not user:
    from app.utils.security import get_password_hash
    user = User(name='Tester', email='tester@deepguard.ai', hashed_password=get_password_hash('TestPass123!'), is_verified=True, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
token = create_access_token({'sub': user.email})
db.close()

def test_upload(file_path, endpoint_suffix, content_type='image/jpeg'):
    url = f'http://127.0.0.1:8000/api/analysis/{endpoint_suffix}'
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        file_bytes = f.read()
    
    header = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: {content_type}\r\n\r\n'
    ).encode('utf-8')
    footer = f'\r\n--{boundary}--\r\n'.encode('utf-8')
    body = header + file_bytes + footer
    
    req = urllib.request.Request(url, data=body, headers={
        'Content-Type': f'multipart/form-data; boundary={boundary}',
        'Authorization': f'Bearer {token}'
    }, method='POST')
    
    try:
        with urllib.request.urlopen(req) as resp:
            print(f'{filename} ({endpoint_suffix}): Status {resp.status}')
            data = json.loads(resp.read().decode())
            print('Response:', data)
            if 'analysis_id' in data:
                detail_req = urllib.request.Request(f'http://127.0.0.1:8000/api/analysis/{data["analysis_id"]}', headers={'Authorization': f'Bearer {token}'})
                with urllib.request.urlopen(detail_req) as d_resp:
                    detail = json.loads(d_resp.read().decode())
                    print('Analysis Detail:', detail)
    except urllib.error.HTTPError as e:
        print(f'{filename} ({endpoint_suffix}): HTTPError {e.code} -> {e.read().decode()}')
    except Exception as e:
        print(f'{filename} ({endpoint_suffix}): Exception -> {e}')

if __name__ == '__main__':
    test_upload('../ai/evaluation/real/033.jpg', 'image', 'image/jpeg')
    test_upload('../ai/evaluation/manipulated/001.jpg', 'image', 'image/jpeg')
