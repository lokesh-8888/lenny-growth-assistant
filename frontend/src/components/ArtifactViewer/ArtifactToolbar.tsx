import React from 'react';
import { ArtifactControls } from './ArtifactControls';
import type { ArtifactControlsProps, ViewTab } from './ArtifactControls';

export type { ViewTab };
export interface ArtifactToolbarProps extends ArtifactControlsProps {}

export const ArtifactToolbar: React.FC<ArtifactToolbarProps> = (props) => {
  return <ArtifactControls {...props} />;
};

export { ArtifactControls };
