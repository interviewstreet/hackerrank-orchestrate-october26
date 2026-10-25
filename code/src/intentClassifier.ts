import type {
  RequestIntentClassification,
  RequestIntentReason,
} from "./types.ts";

const DELETION_ACTION =
  /\b(?:delete|deleting|deleted|deletion|erase|erasing|erased|erasure|remove|removing|removed|removal|close|closing|closed|closure|cancel|canceling|cancelled|cancellation|elimin[a-záéíóúñ]*|borr[a-záéíóúñ]*|suprim[a-záéíóúñ]*|cerr[a-záéíóúñ]*|suppression|supprim[a-zàâçéèêëîïôûùüÿæœ]*|effac[a-zàâçéèêëîïôûùüÿæœ]*|ferm[a-zàâçéèêëîïôûùüÿæœ]*|exclu[a-záéíóúãõç]*|exclus[a-záéíóúãõç]*|apag[a-záéíóúãõç]*|delet[a-záéíóúãõç]*|encerr[a-záéíóúãõç]*)\b|削除|消去|삭제|탈퇴/i;

const DELETION_TARGET =
  /\b(?:account|cuenta|compte|conta|profile|perfil|profil|personal\s+(?:data|information|details)|data\s+about\s+me|my\s+(?:data|information|records|details)|records?|registros?|enregistrements?|identifiers?|identifiants?|identificadores?|name|nombre|contact\s+details|coordonn[ée]es?|email|correo|phone|tel[eé]fonos?|telefone|analytics\s+data|support\s+(?:messages|conversations|attachments)|search\s+results?|export\s+files?|backups?|archives?|datos(?:\s+personales)?|donn[ée]es?(?:\s+personnelles?)?|dados(?:\s+pessoais)?|informacion(?:\s+personal)?|información(?:\s+personal)?|informations?\s+personnelles?)\b|アカウント|個人情報|識別情報|データ|プロフィール|계정|개인정보|식별 정보|데이터|프로필/i;

const NEGATED_DELETION_ACTIONS = [
  /\b(?:do\s+not|don['’]?t|never|cannot|can\s+not|can['’]?t)\s+(?:(?:want|need|wish)\s+(?:(?:you|anyone|someone|anybody|them|us)\s+)?to\s+)?(?:delete|deleting|deletion|erase|erasing|erasure|remove|removing|removal|close|closing|closure|cancel|cancellation)\b/gi,
  /\bwithout\s+(?:deleting|erasing|removing|closing|canceling)\b/gi,
  /\bno\s+(?:(?:quiero|deseo|solicito)\s+)?(?:borrar|eliminar|suprimir|cerrar)\b/gi,
  /\bnao\s+(?:(?:quero|desejo|solicito)\s+)?(?:apagar|excluir|deletar|encerrar)\b/gi,
  /\bne\b[^.!?]{0,24}\bpas\b[^.!?]{0,16}\b(?:supprimer|effacer|fermer)\b/gi,
  /(?:削除|消去)(?:しない|しません|しないで)|(?:삭제|탈퇴)하지\s*않/gi,
];

const VERIFICATION_REQUEST =
  /\b(?:verify|confirm|check|audit|inspect|review|comprobar|verificar|confirmar|revisar|verifier|confirmer|controler)\b|確認|検証|확인|검토/i;

const DELETED_STATE =
  /\b(?:deleted|erased|removed|gone|no\s+longer\s+exists?|fully\s+removed|fully\s+deleted|already\s+removed|eliminad[oa]s?|borrad[oa]s?|suprimid[oa]s?|supprim[eé]s?|effac[eé]s?|exclu[ií]d[oa]s?|apagados?|supprim[eé]s?|desaparecid[oa]s?)\b|削除済み|消えた|削除された|삭제되|사라진/i;

function normalizeText(value: string): string {
  return value.normalize("NFKC").toLowerCase().replace(/\s+/g, " ").trim();
}

function removeNegatedDeletionPhrases(text: string): string {
  return NEGATED_DELETION_ACTIONS.reduce(
    (result, pattern) => result.replace(pattern, " "),
    text,
  );
}

function hasDeletionActionAndTarget(text: string): boolean {
  const sentences = text.split(/[.!?;:。！？\n]+/);
  return sentences.some(
    (sentence) => DELETION_ACTION.test(sentence) && DELETION_TARGET.test(sentence),
  );
}

function hasPriorDeletionVerification(text: string): boolean {
  return (
    VERIFICATION_REQUEST.test(text) &&
    DELETED_STATE.test(text) &&
    DELETION_TARGET.test(text)
  );
}

export function classifyDeletionIntent(
  requestText: string,
): RequestIntentClassification {
  const normalizedText = normalizeText(requestText);
  const affirmativeText = removeNegatedDeletionPhrases(normalizedText);
  const hasDeletionRequest = hasDeletionActionAndTarget(affirmativeText);
  const hasDeletionVerification = hasPriorDeletionVerification(normalizedText);

  if (hasDeletionRequest || hasDeletionVerification) {
    return {
      intent: "DELETE_REQUEST",
      reason: hasDeletionVerification
        ? "VERIFY_PRIOR_DELETION"
        : "EXPLICIT_DELETION",
    };
  }

  const reason: RequestIntentReason = "NO_CLEAR_DELETION_AUTHORIZATION";
  return { intent: "OTHER_REQUEST", reason };
}
