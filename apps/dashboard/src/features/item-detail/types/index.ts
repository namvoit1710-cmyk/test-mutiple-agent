export interface IItem {
  id: string;
  name: string;
  description: string;
  value: number;
}

export type ItemDetailResponse = {
  data: IItem;
};
