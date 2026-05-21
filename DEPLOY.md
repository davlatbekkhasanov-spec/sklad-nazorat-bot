# Deploy — ma’lumotlar saqlanishi

## Nima saqlanadi (`sklad_bot.db`)

- Aktiv **tsikl** va barcha **hisobotlar** (`submissions`)
- Xodimlar, Telegram ID, parollar
- Papka biriktirishlari (`assignments`)

## Deploydan keyin «0 dan» bo‘lib qolmasligi

1. `DB_PATH=sklad_bot.db` ni `.env` da qoldiring.
2. Serverda **doimiy disk (volume)** bog‘lang — Railway / VPS da `sklad_bot.db` fayli saqlanadigan papka.
3. Yangi kod + `groups.xlsx` deploy qilinganda bot **ishga tushganda** Excel bilan `assignments` ni **sinxronlaydi** (`sync_assignments_from_excel`):
   - Excelda yo‘q eski biriktirishlar **o‘chiriladi**
   - Yangilar **qo‘shiladi**
   - Tsikl va hisobotlar **o‘chirilmaydi**

## Papkalar qayta taqsimlanganda (2026-05)

`Ражаббоев Пулат` va `Сагдуллаев Юнус` papkalari 5 ta xodimga bo‘lingan (`groups.xlsx`).

**Eslatma:** agar **aktiv tsikl** davom etayotgan bo‘lsa va Пулат/Юнус allaqachon ba’zi papkalar bo‘yicha hisobot topshirgan bo‘lsa, shu papkalar boshqa xodimga o‘tgach **yana topshirish** mumkin (hisobot xodim+tsikl+papka bo‘yicha). Xavfsiz variant: tsiklni yopib, keyin deploy qilish.

## Qo‘lda sinxron

Admin lichkada: **📥 Excel импорт** yoki `/reimport`
