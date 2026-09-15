import React from 'react';
import { QuickActions } from './QuickActions';

export interface ArtifactActionToolbarProps {
  messageId: string;
}

export const ArtifactActionToolbar: React.FC<ArtifactActionToolbarProps> = (props) => {
  return <QuickActions {...props} />;
};
