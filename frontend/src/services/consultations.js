import { api } from "./api";

export const consultationsService = {
  async create(prompt) {
    const response = await api.post("/api/consultations/", { prompt });
    return response.data;
  },
  async list() {
    const response = await api.get("/api/consultations/");
    return response.data;
  },
  async detail(id) {
    const response = await api.get(`/api/consultations/${id}/`);
    return response.data;
  },
  async remove(id) {
    await api.delete(`/api/consultations/${id}/`);
  },
};
