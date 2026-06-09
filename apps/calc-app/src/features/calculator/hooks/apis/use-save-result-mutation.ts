import { useMutation } from "@tanstack/react-query";
import { calculatorApi } from "./calculator-api";
import { ISaveResultRequest } from "../../types/calculator";

export const useSaveResultMutation = () => {
  return useMutation({
    mutationFn: (data: ISaveResultRequest) => calculatorApi.saveResult(data),
    onSuccess: (data) => {
      console.log("Successfully saved result:", data.id);
      // In a real app, we would use a toast here
    },
    onError: (error) => {
      console.error("Failed to save result:", error);
    },
  });
};
