"""Új háztartás induló adatai: kategóriák és általános (nem személyes) kereskedő-szabályok."""

KATEGORIAK = [
    ("Élelmiszer", "kiadas", "cart"), ("Étterem", "kiadas", "silverware-fork-knife"), ("Rezsi", "kiadas", "flash"),
    ("Szórakozás", "kiadas", "film"), ("Ruházat", "kiadas", "shirt"), ("Közlekedés", "kiadas", "car"),
    ("Egészség", "kiadas", "heart-pulse"), ("Előfizetés", "kiadas", "calendar-sync"), ("Banki költségek", "kiadas", "bank"), ("Háztartás", "kiadas", "home-variant"),
    ("Törlesztés", "kiadas", "credit-card-clock"), ("Átutalás", "kiadas", "bank-transfer-out"),
    ("Gazdaság", "kiadas", "sprout"), ("Egyéb", "kiadas", "ellipsis-horizontal"),
    ("Belső átvezetés", "atvezetes", "swap-horizontal"),
    ("Fizetés", "bevetel", "cash"), ("Egyéb bevétel", "bevetel", "cash-plus"),
]

SZABALYOK = [
    ("lidl", "Élelmiszer"), ("spar", "Élelmiszer"), ("tesco", "Élelmiszer"), ("aldi", "Élelmiszer"), ("penny", "Élelmiszer"),
    ("coop", "Élelmiszer"), ("cba", "Élelmiszer"), ("kifli", "Élelmiszer"),
    ("mvm", "Rezsi"), ("telekom", "Rezsi"), ("digi", "Rezsi"), ("vodafone", "Rezsi"), ("yettel", "Rezsi"),
    ("netflix", "Előfizetés"), ("spotify", "Előfizetés"), ("apple.com/bill", "Előfizetés"), ("google workspace", "Előfizetés"),
    ("youtube", "Előfizetés"), ("claude.ai", "Előfizetés"),
    ("mol", "Közlekedés"), ("omv", "Közlekedés"), ("shell", "Közlekedés"),
    ("mcd", "Étterem"), ("kfc", "Étterem"), ("burger king", "Étterem"), ("pizza hut", "Étterem"), ("pizzeria", "Étterem"),
    ("patika", "Egészség"), ("gyógyszertár", "Egészség"),
    ("tranzakció költsége", "Banki költségek"), ("megb.díj", "Banki költségek"), ("havidíj", "Banki költségek"),
    ("munkabér", "Fizetés"),
]
