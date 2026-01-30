import { test, expect } from '@playwright/test';

test.describe('CV Optimization Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the optimize page before each test
    await page.goto('http://localhost:5173/optimize');
  });

  test('should complete CV optimization flow successfully', async ({ page }) => {
    // Step 1: Select resume source (upload)
    await page.getByLabel('Resume Source').click();
    await page.getByRole('option', { name: 'Upload New Resume' }).click();

    // Upload a mock resume file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'resume.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('Mock resume content for testing'),
    });

    // Verify file upload success
    await expect(page.getByText('resume.pdf')).toBeVisible();

    // Click Next
    await page.getByRole('button', { name: 'Next' }).click();

    // Step 2: Fill job details
    await page.getByLabel('Company').fill('Tech Corp');
    await page.getByLabel('Position').fill('Senior Software Engineer');
    await page.getByLabel('Job Description').fill('We are looking for a Senior Software Engineer with 5+ years of experience in Python and FastAPI.');

    // Click Next
    await page.getByRole('button', { name: 'Next' }).click();

    // Step 3: Select template
    await page.getByLabel('Choose Template').click();
    await page.getByRole('option', { name: 'Modern' }).click();

    // Toggle cover letter generation
    await page.getByLabel('Generate Cover Letter').check();

    // Click Next
    await page.getByRole('button', { name: 'Next' }).click();

    // Step 4: Review and submit
    await expect(page.getByText('Review Your Details')).toBeVisible();
    await expect(page.getByText('Source: Uploaded File')).toBeVisible();
    await expect(page.getByText('Company: Tech Corp')).toBeVisible();
    await expect(page.getByText('Position: Senior Software Engineer')).toBeVisible();
    await expect(page.getByText('Template: Modern')).toBeVisible();
    await expect(page.getByText('Cover Letter: Yes')).toBeVisible();

    // Click Analyze & Optimize
    await page.getByRole('button', { name: 'Analyze & Optimize' }).click();

    // Verify navigation to analysis page
    await expect(page).toHaveURL(/.*\/analysis/);
    await expect(page.getByText('Analysis Results')).toBeVisible();
  });

  test('should show error if required fields are missing', async ({ page }) => {
    // Attempt to click Next without selecting a resume source
    await page.getByRole('button', { name: 'Next' }).click();

    // Verify error message
    await expect(page.getByText('Please select a resume source')).toBeVisible();
  });

  test('should navigate back and forth between steps', async ({ page }) => {
    // Step 1: Select resume source
    await page.getByLabel('Resume Source').click();
    await page.getByRole('option', { name: 'Upload New Resume' }).click();

    // Click Next
    await page.getByRole('button', { name: 'Next' }).click();

    // Step 2: Fill job details
    await page.getByLabel('Company').fill('Tech Corp');

    // Click Previous
    await page.getByRole('button', { name: 'Previous' }).click();

    // Verify navigation back to Step 1
    await expect(page.getByText('Step 1: Select Source')).toBeVisible();

    // Click Next again
    await page.getByRole('button', { name: 'Next' }).click();

    // Verify job details are preserved
    await expect(page.getByLabel('Company')).toHaveValue('Tech Corp');
  });
});
