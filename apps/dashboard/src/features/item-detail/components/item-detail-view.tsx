import React, { FC } from "react";
import { IItem } from "../types";
import { LoadingOverlay } from "@ldc/ui";

interface ItemDetailViewProps {
  item: IItem | undefined;
  isLoading: boolean;
}

export const ItemDetailView: FC<ItemDetailViewProps> = ({ item, isLoading }) => {
  return (
    <LoadingOverlay loading={isLoading}>
      {item ? (
        <div className="p-4 space-y-4">
          <h1 className="text-2xl font-bold">{item.name}</h1>
          <p className="text-gray-600">{item.description}</p>
          <div className="text-lg font-medium">Value: {item.value}</div>
        </div>
      ) : (
        !isLoading && <p>Item not found.</p>
      )}
    </LoadingOverlay>
  );
};
