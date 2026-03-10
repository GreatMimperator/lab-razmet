import os
import json
import shutil
import argparse
import requests
import wikipediaapi
import time

USER_AGENT = 'ABOBA/1.0 (mailto:aboba@itmo.ru)'
WIKI_LANG = 'ru'
BASE_DATA_DIR = 'data'
REPLACEMENTS_DIR = 'replacements'
FOLDERS = ['audio', 'image', 'text']

wiki_wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=WIKI_LANG)

def setup_args():
    parser = argparse.ArgumentParser(description="Парсер датасета видов транспорта")
    parser.add_argument('--clear', action='store_true', help="Полная очистка папки data перед запуском")
    return parser.parse_args()

def get_image_url(name):
    """Умный поиск фото в Википедии (сначала инфобокс, потом тело статьи)"""
    api_url = "https://ru.wikipedia.org/w/api.php"
    # Попытка через pageimages
    params = {"action": "query", "titles": name, "prop": "pageimages", "format": "json", "pithumbsize": "1000"}
    try:
        data = requests.get(api_url, params=params, headers={'User-Agent': USER_AGENT}).json()
        pages = data['query']['pages']
        p_id = list(pages.keys())[0]
        if 'thumbnail' in pages[p_id]:
            return pages[p_id]['thumbnail']['source']
        
        # Попытка через поиск всех картинок на странице
        params = {"action": "query", "titles": name, "prop": "images", "format": "json"}
        data = requests.get(api_url, params=params, headers={'User-Agent': USER_AGENT}).json()
        pages = data['query']['pages']
        p_id = list(pages.keys())[0]
        if 'images' in pages[p_id]:
            for img in pages[p_id]['images']:
                title = img['title']
                if title.lower().endswith(('.jpg', '.jpeg', '.png')):
                    p_info = {"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url", "format": "json"}
                    info = requests.get(api_url, params=p_info, headers={'User-Agent': USER_AGENT}).json()
                    i_id = list(info['query']['pages'].keys())[0]
                    return info['query']['pages'][i_id]['imageinfo'][0]['url']
    except: pass
    return None

def main():
    args = setup_args()

    if not os.path.exists('transports.json'):
        print("[!] Ошибка: Файл transports.json не найден!")
        return
    with open('transports.json', 'r', encoding='utf-8') as f:
        transports = json.load(f)

    if args.clear:
        if os.path.exists(BASE_DATA_DIR):
            print(f"[*] Очистка только рабочей папки '{BASE_DATA_DIR}'...")
            shutil.rmtree(BASE_DATA_DIR)
            print(f"  [✔] Папка '{BASE_DATA_DIR}' удалена. Папка '{REPLACEMENTS_DIR}' сохранена.")
        else:
            print(f"[*] Папка '{BASE_DATA_DIR}' не существует, очищать нечего.")

    for f in FOLDERS:
        os.makedirs(os.path.join(BASE_DATA_DIR, f), exist_ok=True)
        os.makedirs(os.path.join(REPLACEMENTS_DIR, f), exist_ok=True)

    for name in transports:
        print(f"\n>>> Обработка: {name}")

        for folder in FOLDERS:
            target_dir = os.path.join(BASE_DATA_DIR, folder)
            repl_dir = os.path.join(REPLACEMENTS_DIR, folder)
            
            repl_files = [f for f in os.listdir(repl_dir) if os.path.splitext(f)[0] == name]
            
            if repl_files:
                existing_in_data = [f for f in os.listdir(target_dir) if os.path.splitext(f)[0] == name]
                for f_to_del in existing_in_data:
                    os.remove(os.path.join(target_dir, f_to_del))

                file_to_copy = repl_files[0]
                shutil.copy2(os.path.join(repl_dir, file_to_copy), os.path.join(target_dir, file_to_copy))
                print(f"  [+] {folder.upper()}: Заменено файлом из replacements.")
                continue

            existing_in_data = [f for f in os.listdir(target_dir) if os.path.splitext(f)[0] == name]
            if existing_in_data:
                print(f"  [-] {folder.upper()}: Уже существует, пропускаю.")
                continue

            if folder == 'text':
                try:
                    page = wiki_wiki.page(name)
                    if page.exists():
                        with open(os.path.join(target_dir, f"{name}.md"), "w", encoding="utf-8") as f_text:
                            f_text.write(f"# {name}\n\n{page.summary}")
                        print(f"  [+] TEXT: Скачано из Википедии.")
                except Exception as e: print(f"  [!] TEXT ошибка: {e}")

            elif folder == 'image':
                try:
                    url = get_image_url(name)
                    if url:
                        resp = requests.get(url, headers={'User-Agent': USER_AGENT})
                        ext = url.split('.')[-1].lower()
                        
                        with open(os.path.join(target_dir, f"{name}.{ext}"), 'wb') as f_img:
                            f_img.write(resp.content)
                        print(f"  [+] IMAGE: Скачано из Википедии.")
                        time.sleep(1) # Небольшая задержка
                    else: print(f"  [-] IMAGE: Не найдено.")
                except Exception as e: print(f"  [!] IMAGE ошибка: {e}")
            
            elif folder == 'audio':
                print(f"  [-] AUDIO: Файл не найден в replacements и не скачивается автоматически.")

    print("\n[✔] Готово! Всё в папке 'data'.")

if __name__ == "__main__":
    main()