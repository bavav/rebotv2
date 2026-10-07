import json
from ....app.services.svm_model import SVMEmbeddingSpamClassifier

texts, labels = [], []
with open("./workers/ads_worker/app/shieldmodel/svm/service/start.jsonl", encoding="utf-8") as f:
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

clf = SVMEmbeddingSpamClassifier(model_dir="./workers/ads_worker/app/shieldmodel/svm", threshold=0.5)
clf.load()
from collections import Counter
print(Counter(labels))
result = clf.train(texts, labels)
print(result)
if result["trained"]:
    clf.save()