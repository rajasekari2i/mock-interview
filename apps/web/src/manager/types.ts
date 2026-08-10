export type JobDescriptionSourceType = "MANUAL" | "UPLOAD";
export type JobDescriptionFormat = "PDF" | "DOCX" | "TXT" | null;

export interface ManagerJobDescription {
  id: string;
  title: string;
  sourceType: JobDescriptionSourceType;
  sourceFormat: JobDescriptionFormat;
  createdAt: string;
}

export interface ManagerJobDescriptionPage {
  items: ManagerJobDescription[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface ManagerCandidate {
  id: string;
  displayName: string;
  email: string;
}

export interface ManagerCandidatePage {
  items: ManagerCandidate[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface ManagerInterview {
  id: string;
  candidate: ManagerCandidate;
  jobDescription: { id: string; title: string };
  scheduledAt: string;
  status: "SCHEDULED";
}

export interface ManagerInterviewPage {
  items: ManagerInterview[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}
