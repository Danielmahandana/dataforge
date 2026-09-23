import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/layout/Layout';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { Documents } from './pages/Documents';
import { Pipeline } from './pages/Pipeline';
import { Datasets } from './pages/Datasets';
import { DatasetDetails } from './pages/DatasetDetails';
import { Validation } from './pages/Validation';
import { Review } from './pages/Review';
import { Exports } from './pages/Exports';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5000,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/datasets" element={<Datasets />} />
            <Route path="/datasets/:datasetId" element={<DatasetDetails />} />
            <Route path="/validation" element={<Validation />} />
            <Route path="/review" element={<Review />} />
            <Route path="/exports" element={<Exports />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
