import { api } from "./api";

export const consultationsService = {
  async create(prompt) {
    const response = await api.post("/consultations/", { prompt });
    return response.data;
  },
  async list() {
    const response = await api.get("/consultations/");
    return response.data;
  },
  async detail(id) {
    const response = await api.get(`/consultations/${id}/`);
    return response.data;
  },
  async remove(id) {
    await api.delete(`/consultations/${id}/`);
  },
};
