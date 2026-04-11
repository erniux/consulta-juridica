import { api } from "./api";

export const legalService = {
  async listSources() {
    const response = await api.get("/api/sources/");
    return response.data;
  },
  async listDocuments() {
    const response = await api.get("/api/documents/");
    return response.data;
  },
};
