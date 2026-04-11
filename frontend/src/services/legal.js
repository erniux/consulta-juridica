import { api } from "./api";

export const legalService = {
  async listSources() {
    const response = await api.get("/sources/");
    return response.data;
  },
  async listDocuments() {
    const response = await api.get("/documents/");
    return response.data;
  },
};
