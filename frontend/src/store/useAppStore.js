import { create } from 'zustand';
import apiClient from '../api/client';

export const useAppStore = create((set) => ({
  // Data States
  summary: null,
  themes: [],
  behaviors: [],
  segments: [],
  unmetNeeds: [],
  repetitionCauses: [],
  usage: { tokens_used: 0, requests_made: 0 },
  
  // Loading & Error States
  isLoading: false,
  error: null,
  
  pipelinePreview: null,
  
  // Backend Status
  backendStatus: 'checking', // 'checking' | 'online' | 'offline'
  
  checkBackendStatus: async () => {
    try {
      await apiClient.get('/usage');
      set({ backendStatus: 'online' });
    } catch (e) {
      set({ backendStatus: 'offline' });
    }
  },
  
  // Synchronous Step State
  lastCompletedStep: 0, // 1: Scraped, 2: Preprocessed, 3: Analyzed, 4: Aggregated, 5: Indexed
  activeJobType: null,
  
  fetchPipelinePreview: async () => {
    try {
      const res = await apiClient.get('/pipeline-preview');
      set({ pipelinePreview: res.data });
    } catch (e) {
      console.error("Failed to fetch pipeline preview", e);
    }
  },

  fetchInsights: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await apiClient.get('/insights');
      const data = res.data;
      
      if (Object.keys(data).length > 0) {
        set({
          summary: data.summary,
          themes: data.themes,
          behaviors: data.behaviors,
          segments: data.segments,
          unmetNeeds: data.unmet_needs,
          repetitionCauses: data.repetition_causes,
          usage: data.usage || { tokens_used: 0, requests_made: 0 },
          isLoading: false
        });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      console.error("Failed to fetch insights:", error);
      set({ error: "Failed to load dashboard data.", isLoading: false });
    }
  },
  
  // Synchronous Job Action
  triggerPipeline: async (type, payload) => {
    try {
      set({ activeJobType: type });
      await apiClient.post(`/${type}`, payload || {});
      
      const { fetchPipelinePreview, fetchInsights, lastCompletedStep } = useAppStore.getState();
      let newStep = lastCompletedStep;
      if (type === 'scrape') newStep = 1;
      if (type === 'preprocess') newStep = 2;
      if (type === 'analyze') newStep = 3;
      if (type === 'aggregate') newStep = 4;
      if (type === 'index-chat') newStep = 5;
      
      set({ lastCompletedStep: newStep, activeJobType: null });
      
      if (type === 'scrape' || type === 'preprocess') {
        await fetchPipelinePreview();
      }
      
      if (type === 'aggregate') {
        await fetchInsights();
      }
      
      if (type === 'index-chat') {
        alert("Chatbot Database Synced Successfully!");
      }
      
    } catch (error) {
      console.error(`Failed to trigger ${type}:`, error);
      set({ activeJobType: null });
      throw error;
    }
  }
}));
