import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',timeout:45000,workers:1,use:{baseURL:process.env.GRC_BASE_URL||'http://127.0.0.1:8005',headless:true,viewport:{width:1440,height:1000},trace:'retain-on-failure'},reporter:[['list'],['json',{outputFile:'test-results/results.json'}]]});
