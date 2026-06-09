import { useQuery } from "@ldc/tanstack-query";
import { queryKeyFactory } from "@ldc/tanstack-query";
import { IItem, ItemDetailResponse } from "../../types";

const _itemKeys = queryKeyFactory("items");
export const itemKeys = {
  ..._itemKeys,
};

// Mock API function
const fetchItemDetail = async (id: string): Promise<ItemDetailResponse> => {
  // Simulate API call
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        data: {
          id,
          name: `Item ${id}`,
          description: `This is the detail for item number ${id}`,
          value: Math.floor(Math.random() * 1000),
        },
      });
    }, 500);
  });
};

export const useItemDetail = (id: string) => {
  return useQuery({
    queryKey: itemKeys.detail(id),
    queryFn: () => fetchItemDetail(id),
  });
};
