# Deploy — ma’lumotlar saqlanishi

## Nima saqlanadi (`sklad_bot.db`)

- Aktiv **tsikl** va barcha **hisobotlar** (`submissions`)
- Xodimlar, Telegram ID, parollar
- Papka biriktirishlari (`assignments`)

## Deploydan keyin «0 dan» bo‘lib qolmasligi

1. `DB_PATH=sklad_bot.db` ni `.env` da qoldiring.
2. **Vaqt:** `TZ=Asia/Tashkent` (Railway UTC bo‘lsa soat 5 soat orqada chiqmasin).
3. **Guruh hisoboti:** PNG kartochka (default). O‘chirish: `GROUP_REPORT_CARD=0` — oddiy matn qaytadi.
2. Serverda **doimiy disk (volume)** bog‘lang — Railway / VPS da `sklad_bot.db` fayli saqlanadigan papka.
3. Yangi kod + `groups.xlsx` deploy qilinganda bot **ishga tushganda** Excel bilan `assignments` ni **sinxronlaydi** (`sync_assignments_from_excel`):
   - Excelda yo‘q eski biriktirishlar **o‘chiriladi**
   - Yangilar **qo‘shiladi**
   - Tsikl va hisobotlar **o‘chirilmaydi**

## Papkalar qayta taqsimlanganda (2026-05)

`Ражаббоев Пулат` va `Сагдуллаев Юнус` papkalari 5 ta xodimga bo‘lingan (`groups.xlsx`).

**Eslatma:** agar **aktiv tsikl** davom etayotgan bo‘lsa va Пулат/Юнус allaqachon ba’zi papkalar bo‘yicha hisobot topshirgan bo‘lsa, shu papkalar boshqa xodimga o‘tgach **yana topshirish** mumkin (hisobot xodim+tsikl+papka bo‘yicha). Xavfsiz variant: tsiklni yopib, keyin deploy qilish.

## Ish tartibi

1. **📌 Папкаларни белгилаш** — ходим ўз папкасини белгилайди; **гуруҳга кетмайди**; **📝 Актив текширувларим** рўйхатидан чиқади.
2. **📝 Текширув топшириш** — белгилangan папка бўйича ҳисобот; **гуруҳга дарҳол кетади**.
3. Admin **📂 Қолган папкалар** ёки **📝 Актив текширувларим** — кимда белгилаш/ҳисобот қолганини кўради.

`folder_marks` deployda saqlanadi (volume билан).

## Qo‘lda sinxron

Admin lichkada: **📥 Excel импорт** yoki `/reimport` (assignments Excelga moslash; ходимлар асосан `folder_marks` ishlatadi)
