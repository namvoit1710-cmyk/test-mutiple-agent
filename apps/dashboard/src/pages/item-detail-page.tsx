import React, { FC } from "react";
import { useParams } from "react-router-dom";
import { useItemDetail } from "../features/item-detail/hooks/apis/use-item-detail";
import { ItemDetailView } from "../features/item-detail/components/item-detail-view";

export const ItemDetailPage: FC = () => {
  const { id } = useParams<{ id: string }>();

  if (!id) {
    return <div>No item ID provided.</div>;
  }

  const { data, isLoading, error } = useItemDetail(id);

  if (error) {
    return <div>Error loading item details.</div>;
  }

  return <ItemDetailView item={data?.data} isLoading={isLoading} />;
};
