import os
import sys
import json
import urllib.request
import urllib.error

def ensure_repo(token, repo_name):
    # Try to create the repository
    api_url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ProjeTakip-Updater"
    }
    data = {
        "name": repo_name,
        "description": "Proje Takip Sistemi",
        "private": False,
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True
    }
    
    print(f"Depo kontrol ediliyor/olusturuluyor: {repo_name}...")
    req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Depo basariyla olusturuldu: {repo_name}")
    except urllib.error.HTTPError as e:
        if e.code == 422: # Unprocessable Entity (repo usually exists)
            print(f"Depo zaten mevcut: {repo_name} (veya isim dogrulamadan gecemedi). Devam ediliyor...")
        else:
            print(f"Depo olustururken hata: {e.code} - {e.reason}")
            print(e.read().decode())
            sys.exit(1)

def init_repo(token, repo_owner, repo_name):
    print("Depo baslangic durumu kontrol ediliyor...")
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/README.md"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ProjeTakip-Updater"
    }

    req = urllib.request.Request(api_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            print("Depoda README mevcut. Bos degil.")
            return # Alredy initialized
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("Depo bos gibi gorunuyor, README.md ile baslatiliyor...")
            import base64
            content = "# Proje Takip Sistemi\nGitHub Releases deposu."
            encoded_content = base64.b64encode(content.encode()).decode()
            data = {
                "message": "Initial commit",
                "content": encoded_content,
                "branch": "main"
            }
            put_req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers=headers, method="PUT")
            try:
                with urllib.request.urlopen(put_req) as response:
                    print("Depo basariyla init edildi.")
            except urllib.error.HTTPError as e2:
                print("Repo init hatasi:", e2.code, e2.reason)
                print(e2.read().decode())
        else:
            print("README kontrol hatasi:", e.code, e.reason)

def upload_release():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("HATA: GITHUB_TOKEN bulunamadi.")
        sys.exit(1)

    repo_owner = "SLedgehammer-dev12"
    repo_name = "Proje_Takip"
    tag_name = "v2.1.0"
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ProjeTakip-Updater"
    }
    
    # 1. Ensure Repo Exists
    ensure_repo(token, repo_name)
    init_repo(token, repo_owner, repo_name)

    # 2. Read Release Notes
    with open(r"docs\releases\v2.1.0.md", "r", encoding="utf-8") as f:
        body = f.read()

    data = {
        "tag_name": tag_name,
        "name": f"Proje Takip Sistemi {tag_name}",
        "body": body,
        "draft": False,
        "prerelease": False
    }

    print(f"\n[{tag_name}] release olusturuluyor...")
    req = urllib.request.Request(api_url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            upload_url = res_data["upload_url"].split("{")[0]
            print("Release uretildi! ID:", res_data["id"])
    except urllib.error.HTTPError as e:
        if e.code == 422:
            print("Release zaten var gibi gorunuyor. Oncelikle silinmesi gerekebilir.")
            print(e.read().decode())
            sys.exit(1)
        else:
            print("API Hatasi:", e.code, e.reason)
            print(e.read().decode())
            sys.exit(1)

    # 3. Upload Assets
    assets = [
        (r"release\v2.1.0\ProjeTakip-v2.1.0-windows-x64.exe", "application/vnd.microsoft.portable-executable"),
        (r"release\v2.1.0\SHA256SUMS", "text/plain")
    ]

    for filepath, content_type in assets:
        if not os.path.exists(filepath):
            print(f"HATA: Dosya bulunamadi: {filepath}")
            continue
            
        filename = os.path.basename(filepath)
        print(f"Yukleniyor: {filename}...")
        with open(filepath, "rb") as f:
            file_data = f.read()
        
        asset_req = urllib.request.Request(
            f"{upload_url}?name={filename}", 
            data=file_data, 
            headers={**headers, "Content-Type": content_type}, 
            method="POST"
        )
        try:
            with urllib.request.urlopen(asset_req) as response:
                print(f"Basarili: {filename}")
        except urllib.error.HTTPError as e:
            print(f"Yukleme Hatasi ({filename}):", e.code, e.reason)
            print(e.read().decode())

    print("\nTUM ASAMALAR TAMAMLANDI!")
    print(f"Yayinlanan Adres: https://github.com/{repo_owner}/{repo_name}/releases/tag/{tag_name}")

if __name__ == "__main__":
    upload_release()
