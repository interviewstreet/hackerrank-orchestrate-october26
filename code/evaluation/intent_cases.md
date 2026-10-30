# Intent evaluation set

Fictional request texts written for this project (not taken from the dataset). Each targets one trap of
the "does this request authorize deletion?" decision. `python3 code/evaluation/main.py` scores the offline
heuristic and the LLM classifier on this table together with the 32 public sample requests (all DELETE).

| id | lang | expected | trap | text |
|---|---|---|---|---|
| i01 | en | DELETE | plain | Please delete my account and everything you store about me. |
| i02 | en | DELETE | close wording | I'd like to close my account for good and have my details removed. |
| i03 | en | DELETE | no verb, outcome | Make sure nothing in your systems can identify me after I leave. |
| i04 | en | DELETE | export then delete | Send me a copy of my order history first, then erase the account completely. |
| i05 | en | DELETE | follow-up | My deletion request from last month still shows as pending. Please finish removing my data. |
| i06 | en | DELETE | right to be forgotten | I am exercising my right to be forgotten under GDPR for this account. |
| i07 | en | DELETE | polite, indirect | Could you get rid of my profile? I won't be shopping with you anymore. |
| i08 | en | DELETE | failed self-service | The delete button in the app gave an error. Please remove the account on your side. |
| i09 | en | DELETE | wipe | Wipe my customer profile and any saved addresses. |
| i10 | en | DELETE | purge | Please purge all personal data tied to this email. |
| i11 | en | NON_DELETE | marketing only | Stop sending me newsletters, but keep my account open. |
| i12 | en | NON_DELETE | unsubscribe | Please unsubscribe me from promotional emails. |
| i13 | en | NON_DELETE | export only | I want to download all the data you hold about me in JSON. |
| i14 | en | NON_DELETE | access | What personal information do you have on file for me? |
| i15 | en | NON_DELETE | correction | My last name is spelled wrong on the profile, please fix it. |
| i16 | en | NON_DELETE | phone update | Please update my phone number to the new one I gave the agent. |
| i17 | en | NON_DELETE | invoices | I need copies of my invoices from 2025 for my accountant. |
| i18 | en | NON_DELETE | login help | I'm locked out and need to reset my password. |
| i19 | en | NON_DELETE | explicit do-not-delete | Please don't delete anything, I just want to know where my parcel is. |
| i20 | en | NON_DELETE | delete one field only | Remove the old phone number from my profile but keep the account. |
| i21 | en | NON_DELETE | change email | Please change the email address on my account to my work address. |
| i22 | en | NON_DELETE | delete a saved card | Delete the expired card from my wallet; I still use the account. |
| i23 | es | DELETE | plain | Quiero que eliminen mi cuenta y todos mis datos personales. |
| i24 | es | DELETE | borrar | Por favor, borren mi perfil de forma permanente. |
| i25 | es | NON_DELETE | marketing | Dejen de enviarme publicidad, pero no quiero eliminar mi cuenta. |
| i26 | es | NON_DELETE | export | Necesito una copia de mis datos; la cuenta debe seguir activa. |
| i27 | pt | DELETE | plain | Solicito a exclusão definitiva da minha conta e dos meus dados. |
| i28 | pt | DELETE | apagar | Por favor, apaguem todos os meus dados pessoais. |
| i29 | pt | NON_DELETE | correction | Meu endereço está errado, podem corrigir? Não quero excluir a conta. |
| i30 | pt | NON_DELETE | invoices | Preciso das notas fiscais do último ano, por favor. |
| i31 | fr | DELETE | plain | Je souhaite la suppression de mon compte et de mes données. |
| i32 | fr | DELETE | effacer | Merci d'effacer toutes les informations personnelles liées à cet e-mail. |
| i33 | fr | NON_DELETE | marketing | Je ne veux plus recevoir d'offres, mais je garde mon compte. |
| i34 | fr | NON_DELETE | access | Pouvez-vous m'indiquer quelles données vous détenez sur moi ? |
| i35 | de | DELETE | plain | Bitte löschen Sie mein Konto und alle meine Daten. |
| i36 | de | DELETE | entfernen | Entfernen Sie bitte mein Kundenprofil vollständig. |
| i37 | de | NON_DELETE | export | Ich möchte eine Kopie meiner Daten herunterladen. |
| i38 | de | NON_DELETE | password | Ich habe mein Passwort vergessen und komme nicht mehr ins Konto. |
| i39 | ja | DELETE | plain | アカウントと個人情報をすべて削除してください。 |
| i40 | ja | DELETE | 退会 | 退会して、登録情報を消去してください。 |
| i41 | ja | NON_DELETE | marketing | メールマガジンの配信だけ停止してください。アカウントは削除しないでください。 |
| i42 | ja | NON_DELETE | correction | 登録している電話番号を変更したいです。 |
| i43 | ko | DELETE | plain | 제 계정과 개인정보를 모두 삭제해 주세요. |
| i44 | ko | DELETE | 탈퇴 | 회원 탈퇴를 요청합니다. 저장된 정보도 지워 주세요. |
| i45 | ko | NON_DELETE | marketing | 광고 문자 수신만 거부하고 싶습니다. 계정은 삭제하지 마세요. |
| i46 | ko | NON_DELETE | access | 저에 대해 어떤 정보를 보관하고 있는지 알려 주세요. |
| i47 | en | DELETE | mixed with complaint | Your service was awful and I want my account deleted today. |
| i48 | en | DELETE | check remaining copies | I deleted my account but got an email yesterday. Please remove any copies that are left. |
| i49 | en | NON_DELETE | pause | Can you deactivate my account temporarily while I travel? I'll be back. |
| i50 | en | NON_DELETE | order cancel | Please cancel order ORD-1234 and refund me. |
| i51 | en | NON_DELETE | data question | Do you share my data with third parties? |
| i52 | en | NON_DELETE | keep account | I want to keep my account but remove me from the loyalty program. |
| i53 | es | DELETE | close | Quiero cerrar mi cuenta y que se borre mi información. |
| i54 | fr | NON_DELETE | invoices | J'ai besoin d'une copie de mes factures. |
| i55 | pt | DELETE | close + delete | Encerrem minha conta e excluam os dados associados. |
| i56 | de | NON_DELETE | newsletter | Bitte melden Sie mich nur vom Newsletter ab. |
| i57 | en | DELETE | historical email | This is my old address; please delete the account that used it. |
| i58 | en | NON_DELETE | review deletion only | I'm thinking about deleting my account. What would happen to my order history? |
| i59 | en | DELETE | short | Delete my data. |
| i60 | en | NON_DELETE | short | Update my address. |
| i61 | ja | DELETE | polite | このメールアドレスのアカウントを完全に削除していただけますか。 |
| i62 | ko | NON_DELETE | password | 비밀번호를 재설정하고 싶습니다. |
