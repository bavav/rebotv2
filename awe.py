from .app.services.cascade import cascade

tests = [
    ("н а ш е к а з и н о т о п п и ш и в л с", 1),
    ("Кт0-нибудь открывaл кeйсы в CS2 нeдaвно?", 0),
    ("Кaзин0 с выводом, ccылкa в зaкрепе", 1),
    ("Не реклама, но кaзин0 реально платит, промокод внутри", 1),
    ("Пиздeц, опять рeклaмa кaзин0 в лeнтe.", 0),
    ("бл*ть, опять проиграл на кейсах", 0),
    ("охуенная подработка, 5000 в день, пиши", 1),
]
for t, y in tests:
    p = cascade.predict(t)
    mark = "OK " if int(p.is_spam) == y else "ERR"
    print(f"{mark} y={y} pred={int(p.is_spam)} p={p.proba:.2f} [{p.reason}]")
    print(f"     {t}")