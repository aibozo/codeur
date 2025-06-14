
import { ReactNode, ReactElement } from 'react';

export interface NavItemType {
  name: string;
  icon: ReactNode;
  path: string;
  active?: boolean;
  beta?: boolean;
  count?: number;
}

export interface ActiveAssetType {
  name: string;
  icon: ReactElement; // Changed from ReactNode to React.ReactElement
  amount: string;
  bgColorClass: string;
}

export interface TopAsset {
  id: string;
  name: string;
  shortName: string;
  icon: ReactNode; // Kept as ReactNode as AssetCard doesn't clone this with new props
  rewardRate: string;
  change: string;
  changeType: 'positive' | 'negative';
  chartData: { name: string; value: number }[];
  color: string;
}

export interface ChartDataItem {
  name: string;
  [key: string]: number | string;
}
