export interface CandidateInterview {
  id: string;
  jobDescription: { id: string; title: string };
  scheduledAt: string;
  status: "SCHEDULED";
}

export interface CandidateInterviewPage {
  items: CandidateInterview[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}
