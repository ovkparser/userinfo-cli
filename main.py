import re
import sys
import requests
from colorama import init, Fore, Style
from config import TOKEN, API_VERSION, API_BASE_URL, DEBUG

init()

def debug_print(*args, **kwargs):
    if DEBUG:
        print(f"{Fore.YELLOW}", *args, f"{Style.RESET_ALL}", **kwargs)

def extract_user_id(url):
    # Поддержка числового ID
    if url.isdigit():
        return url
    
    # Поддержка буквенного ID и полных ссылок
    patterns = [
        r'ovk\.to/([a-zA-Z0-9_]+)',  # сначала проверяем username
        r'ovk\.to/id([0-9]+)',  # потом проверяем числовой ID
        r'openvk\.su/([a-zA-Z0-9_]+)',
        r'openvk\.su/id([0-9]+)',
        r'id([0-9]+)',
        r'^([a-zA-Z0-9_]+)$'  # в конце проверяем просто username
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            result = match.group(1)
            debug_print(f"Паттерн = {pattern}")
            debug_print(f"Извлечен идентификатор: {result}")
            return result
    return None

def resolve_screen_name(screen_name):
    params = {
        'access_token': TOKEN,
        'v': API_VERSION,
        'screen_name': screen_name
    }
    
    try:
        response = requests.get(
            f"{API_BASE_URL}utils.resolveScreenName",
            params=params,
            headers={
                'User-Agent': 'OpenVK-CLI-Client/1.0',
                'Accept': 'application/json'
            },
            timeout=10
        )
        
        debug_print(f"Резолв URL = {response.url}")
        response_data = response.json()
        debug_print(f"Ответ резолва = {response_data}")
        
        if 'response' in response_data and response_data['response']:
            return response_data['response'].get('object_id')
    except Exception as e:
        print(f"{Fore.RED}Ошибка при резолве screen_name: {str(e)}{Style.RESET_ALL}")
    return None

def get_user_info(user_id):
    # Если ID не числовой, пробуем резолвить screen_name
    if not user_id.isdigit():
        resolved_id = resolve_screen_name(user_id)
        if resolved_id:
            debug_print(f"ID успешно получен: {resolved_id}")
            user_id = str(resolved_id)
        else:
            print(f"{Fore.RED}Не удалось получить ID пользователя{Style.RESET_ALL}")
            return None

    params = {
        'access_token': TOKEN,
        'v': API_VERSION,
        'user_ids': user_id,
        'fields': 'status,online,sex,interests,counters,verified,banned,blacklisted,photo_200,screen_name,is_closed,can_access_closed,followers_count,wall_count,photos_count,videos_count,audios_count,notes_count,friends_count,groups_count,career,connections,education,universities,schools,relatives,personal,activities,music,movies,tv,books,games'
    }
    
    headers = {
        'User-Agent': 'OpenVK-CLI-Client/1.0',
        'Accept': 'application/json',
        'Origin': 'https://ovk.to',
        'Referer': 'https://ovk.to/',
    }
    
    try:
        response = requests.get(
            f"{API_BASE_URL}users.get",
            params=params,
            headers=headers,
            verify=True,
            timeout=10
        )
        
        debug_print(f"URL запроса = {response.url}")
        debug_print(f"Статус ответа = {response.status_code}")
        debug_print(f"Заголовки ответа = {response.headers}")
        
        if response.status_code != 200:
            print(f"{Fore.RED}Ошибка HTTP: {response.status_code}{Style.RESET_ALL}")
            return None
            
        try:
            response_data = response.json()
            debug_print(f"Ответ API = {response_data}")
            
            if 'error' in response_data:
                error_msg = response_data['error'].get('error_msg', 'Неизвестная ошибка')
                error_code = response_data['error'].get('error_code', 'N/A')
                print(f"{Fore.RED}Ошибка API [{error_code}]: {error_msg}{Style.RESET_ALL}")
                return None
                
            if 'response' in response_data and response_data['response']:
                user_data = response_data['response'][0]
                if isinstance(user_data, dict) and user_data.get('id', 0) != 0:
                    return user_data
                print(f"{Fore.RED}Ошибка: Данные пользователя не найдены в ответе{Style.RESET_ALL}")
                return None
            
        except ValueError:
            print(f"{Fore.RED}Ошибка: Неверный формат ответа от сервера")
            print(f"Ответ: {response.text}{Style.RESET_ALL}")
            return None
            
        debug_print(f"Неожиданный ответ API = {response.text}")
        return None
        
    except requests.exceptions.Timeout:
        print(f"{Fore.RED}Ошибка: Превышено время ожидания ответа от сервера{Style.RESET_ALL}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"{Fore.RED}Ошибка сети: {str(e)}{Style.RESET_ALL}")
        return None

def print_user_info(user_info):
    print(f"\n{Fore.CYAN}=== Информация о пользователе ==={Style.RESET_ALL}\n")
    
    # Основная информация
    verified_badge = f" {Fore.BLUE}✓{Style.RESET_ALL}" if user_info.get('verified') else ""
    print(f"{Fore.GREEN}Имя:{Style.RESET_ALL} {user_info.get('first_name')} {user_info.get('last_name')}{verified_badge}")
    print(f"{Fore.GREEN}ID:{Style.RESET_ALL} {user_info.get('id')}")
    print(f"{Fore.GREEN}Короткое имя:{Style.RESET_ALL} {user_info.get('screen_name', 'Не указано')}")
    print(f"{Fore.GREEN}Ссылка:{Style.RESET_ALL} https://ovk.to/id{user_info.get('id')}")
    
    # Аватарка
    if user_info.get('photo_200'):
        print(f"{Fore.GREEN}Аватарка:{Style.RESET_ALL} {user_info.get('photo_200')}")
    
    # Тип профиля
    privacy = "Закрытый" if user_info.get('is_closed') else "Открытый"
    print(f"{Fore.GREEN}Тип профиля:{Style.RESET_ALL} {privacy}")
    
    # Статус и онлайн
    online_status = "Онлайн" if user_info.get('online') else "Оффлайн"
    print(f"{Fore.GREEN}Статус в сети:{Style.RESET_ALL} {online_status}")
    if user_info.get('status'):
        print(f"{Fore.GREEN}Статус:{Style.RESET_ALL} {user_info.get('status')}")
    
    # Дополнительная информация
    if any(user_info.get(field) for field in ['activities', 'interests', 'music', 'movies', 'tv', 'books', 'games']):
        print(f"\n{Fore.YELLOW}=== Дополнительная информация ==={Style.RESET_ALL}")
        for field, title in [
            ('activities', 'Деятельность'),
            ('interests', 'Интересы'),
            ('music', 'Музыка'),
            ('movies', 'Фильмы'),
            ('tv', 'ТВ'),
            ('books', 'Книги'),
            ('games', 'Игры')
        ]:
            if user_info.get(field):
                print(f"{Fore.GREEN}{title}:{Style.RESET_ALL} {user_info.get(field)}")
    
    # Образование
    if any(user_info.get(field) for field in ['universities', 'schools']):
        print(f"\n{Fore.YELLOW}=== Образование ==={Style.RESET_ALL}")
        if user_info.get('universities'):
            for uni in user_info['universities']:
                print(f"{Fore.GREEN}Университет:{Style.RESET_ALL} {uni.get('name', 'Не указано')}")
        if user_info.get('schools'):
            for school in user_info['schools']:
                print(f"{Fore.GREEN}Школа:{Style.RESET_ALL} {school.get('name', 'Не указано')}")
    
    # Статистика
    print(f"\n{Fore.YELLOW}=== Статистика ==={Style.RESET_ALL}")
    counters = user_info.get('counters', {})
    stats = [
        ('friends_count', 'Друзей'),
        ('followers_count', 'Подписчиков'),
        # ('wall_count', 'Записей'), // Починю позже, эта хуйня не работает
        ('photos_count', 'Фотографий'),
        # ('videos_count', 'Видеозаписей'), // Эту хуйню тоже починю позже, она не работает
        ('audios_count', 'Аудиозаписей'),
        ('notes_count', 'Заметок'),
        ('groups_count', 'Групп')
    ]
    
    for counter, title in stats:
        value = counters.get(counter, user_info.get(counter, 0))
        print(f"{Fore.GREEN}{title}:{Style.RESET_ALL} {value}")

def main():
    print(f"{Fore.CYAN}OVK UserInfo (CLI){Style.RESET_ALL}")
    print("Введите ссылку на профиль или ID пользователя:")
    
    user_input = input().strip()
    user_id = extract_user_id(user_input)
    
    if not user_id:
        print(f"{Fore.RED}Ошибка: Неверный формат ссылки или ID{Style.RESET_ALL}")
        return
    
    user_info = get_user_info(user_id)
    if not user_info:
        print(f"{Fore.RED}Ошибка: Не удалось получить информацию о пользователе{Style.RESET_ALL}")
        return
    
    print_user_info(user_info)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}Программа завершена пользователем{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"{Fore.RED}Произошла ошибка: {str(e)}{Style.RESET_ALL}")
