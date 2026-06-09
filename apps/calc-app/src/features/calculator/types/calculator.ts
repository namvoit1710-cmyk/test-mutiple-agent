export interface ISaveResultRequest {
  num1: number;
  num2: number;
  result: number;
}

export interface ISaveResultResponse {
  id: string;
  status: "success";
}
