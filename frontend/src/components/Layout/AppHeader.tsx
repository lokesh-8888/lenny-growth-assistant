import React from 'react';
import { Header } from './Header';
import type { HeaderProps } from './Header';

export interface AppHeaderProps extends HeaderProps {}

export const AppHeader: React.FC<AppHeaderProps> = (props) => {
  return <Header {...props} />;
};

export { Header };
