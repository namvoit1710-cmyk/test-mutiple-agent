import { ISaveResultRequest, ISaveResultResponse } from "../types/calculator";

export const calculatorApi = {
  saveResult: async (data: ISaveResultRequest): Promise<ISaveResultResponse> => {
    // Simulate API call
    console.log("Saving result to API:", data);
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          id: Math.random().toString(36).substring(7),
          status: "success",
        });
      }, 500);
    });
  },
};
