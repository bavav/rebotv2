import re

def parse(text:str):
    text = text.lower()
    pairs = re.findall(r'(\d+)\s*([а-яa-z]+)',text)
    if not pairs:
        return None
    total
    for a_str,unit in pairs:
        a = int(a_str)

        if unit.startswith(("мес",'mon')):
            total += a * 2592000
        elif unit.startswith(("нед",'mon')):
            total += a * 604800
        elif unit.startswith(("дн",'де','д','d')):
            total += a * 86400
        elif unit.startswith(("час",'ч','h')):
            total += a * 3600
        elif unit.startswith(("м","мин",'m')):
            total += a * 60
        elif unit.startswith(("сек","с",'s')):
            total += a
    return total
def parse_rs(text: str):
    pairs = re.findall(r'(\d+)\s*([а-яa-z]+)', text.lower())
        
    if pairs:
        # Считаем секунды через нашу прошлую логику
        parsed_seconds = 0
        for amount_str, unit in pairs:
            amount = int(amount_str)
            if unit.startswith(('мес', 'mon')): parsed_seconds += amount * 2592000
            elif unit.startswith(('нед', 'w')): parsed_seconds += amount * 604800
            elif unit.startswith(('дн', 'де', 'д', 'd')): parsed_seconds += amount * 86400
            elif unit.startswith(('час', 'ч', 'h')): parsed_seconds += amount * 3600
            elif unit.startswith(('мин', 'м', 'm')): parsed_seconds += amount * 60
            elif unit.startswith(('сек', 'с', 's')): parsed_seconds += amount
        
        if parsed_seconds > 0:
            seconds = parsed_seconds
        
        # --- ОТДЕЛЕНИЕ ПРИЧИНЫ ---
        # Находим индекс, где заканчивается последняя временная пара
        # Ищем последнее совпадение в строке
        last_match = list(re.finditer(r'(\d+)\s*([а-яa-z]+)', text.lower()))[-1]
        end_index = last_match.end()
        
        # Все, что идет после времени — это причина
        potential_reason = text[end_index:].strip()
        time_text = text[:end_index].strip()
        
        if potential_reason:
            reason = potential_reason
    else:
        # Если цифр времени вообще нет (например, "/mute спам"), 
        # то всё написанное считаем причиной, а время берем дефолтное
        reason = text
    return (seconds if seconds else 0), (reason if reason else "Без причины"), (time_text if time_text else "Навсегда")