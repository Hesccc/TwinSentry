import React from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { MainLayout } from '@/layouts/MainLayout';
import { Login } from '@/views/Login';
import { Dashboard } from '@/views/Dashboard';
import { Alerts } from '@/views/Alerts';
import { Audit } from '@/views/Audit';
import { Settings } from '@/views/Settings';
import { Skills } from '@/views/Skills';
import { Profile } from '@/views/Profile';
import { Workflow } from '@/views/Workflow';
import { Prompts } from '@/views/Prompts';
import { Workbench } from '@/views/Workbench';

// Guard for protected routes
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('ts_token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <MainLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: 'alerts',
        element: <Alerts />,
      },
      {
        path: 'skills',
        element: <Skills />,
      },
      {
        path: 'audit',
        element: <Audit />,
      },
      {
        path: 'settings',
        element: <Settings />,
      },
      {
        path: 'profile',
        element: <Profile />,
      },
      {
        path: 'workbench',
        element: <Workbench />,
      },
      {
        path: 'workflow',
        element: <Workflow />,
      },
      {
        path: 'prompts',
        element: <Prompts />,
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);





