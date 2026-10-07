import json
from ....app.services.gbm_model import GradientBoostingSpamClassifier

texts, labels = [], []
with open("./workers/ads_worker/app/shieldmodel/gbm/service/start.jsonl", encoding="utf-8") as f:
    for line in f:
        # Убираем пробелы и переносы строк по краям
        clean_line = line.strip()
        
        # Если строка пустая, пропускаем её
        if not clean_line:
            continue
            
        print(clean_line)
        ex = json.loads(clean_line)
        texts.append(ex["text"])
        labels.append(ex["label"])

clf = GradientBoostingSpamClassifier(model_dir="./workers/ads_worker/app/shieldmodel/gbm", threshold=0.5)

from collections import Counter
print(Counter(labels))
result = clf.train(texts, labels)
print(result)
if result["trained"]:
    clf.save()