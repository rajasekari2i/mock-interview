import { authFetch } from "../auth/api";
import { decodeCandidateInterviewPage } from "./decoders";
import type { CandidateInterviewPage } from "./types";

export async function fetchCandidateInterviews(page = 1): Promise<CandidateInterviewPage> {
  const response = await authFetch(`/candidate/interviews?page=${String(page)}&pageSize=25`);
  return decodeCandidateInterviewPage(await response.json());
}
