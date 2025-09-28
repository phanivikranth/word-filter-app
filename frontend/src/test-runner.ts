/**
 * Frontend Test Runner
 * Comprehensive testing utilities for the Word Filter Frontend
 */

import { exec } from 'child_process';
import { promises as fs } from 'fs';
import * as path from 'path';

interface TestConfig {
  environment: 'development' | 'ci' | 'debug' | 'headless';
  coverage: boolean;
  watch: boolean;
  singleRun: boolean;
  browsers: string[];
  reporters: string[];
}

interface TestResults {
  success: boolean;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  coverage?: {
    statements: number;
    branches: number;
    functions: number;
    lines: number;
  };
}

class FrontendTestRunner {
  private readonly projectRoot: string;
  private readonly coverageDir: string;

  constructor() {
    this.projectRoot = path.resolve(__dirname, '..');
    this.coverageDir = path.join(this.projectRoot, 'coverage');
  }

  /**
   * Run all tests
   */
  async runAllTests(): Promise<TestResults> {
    console.log('🧪 Starting Frontend Test Suite...\n');

    const config: TestConfig = {
      environment: 'development',
      coverage: true,
      watch: false,
      singleRun: true,
      browsers: ['ChromeHeadlessLocal'],
      reporters: ['progress', 'coverage']
    };

    try {
      const results = await this.executeTests(config);
      
      if (results.success) {
        console.log('\n✅ All frontend tests passed successfully!');
        await this.generateTestReport(results);
      } else {
        console.log('\n❌ Some frontend tests failed.');
      }

      return results;
    } catch (error) {
      console.error('\n💥 Test execution failed:', error);
      throw error;
    }
  }

  /**
   * Run tests in watch mode for development
   */
  async runWatchMode(): Promise<void> {
    console.log('👀 Starting Frontend Tests in Watch Mode...\n');

    const config: TestConfig = {
      environment: 'development',
      coverage: false,
      watch: true,
      singleRun: false,
      browsers: ['Chrome'],
      reporters: ['progress', 'kjhtml']
    };

    await this.executeTests(config);
  }

  /**
   * Run tests for CI environment
   */
  async runCITests(): Promise<TestResults> {
    console.log('🔧 Running Frontend Tests in CI Mode...\n');

    const config: TestConfig = {
      environment: 'ci',
      coverage: true,
      watch: false,
      singleRun: true,
      browsers: ['ChromeHeadlessCI'],
      reporters: ['progress', 'coverage']
    };

    const results = await this.executeTests(config);
    
    // Generate CI-friendly reports
    await this.generateCIReport(results);
    
    return results;
  }

  /**
   * Run specific test suites
   */
  async runTestSuite(pattern: string): Promise<TestResults> {
    console.log(`🎯 Running Frontend Test Suite: ${pattern}\n`);

    const config: TestConfig = {
      environment: 'development',
      coverage: true,
      watch: false,
      singleRun: true,
      browsers: ['ChromeHeadlessLocal'],
      reporters: ['progress', 'coverage']
    };

    return await this.executeTests(config, pattern);
  }

  /**
   * Execute tests with given configuration
   */
  private async executeTests(config: TestConfig, pattern?: string): Promise<TestResults> {
    return new Promise((resolve, reject) => {
      // Set environment variables
      const env = {
        ...process.env,
        CI: config.environment === 'ci' ? 'true' : undefined,
        HEADLESS: config.environment === 'headless' ? 'true' : undefined,
        NODE_ENV: config.environment === 'debug' ? 'debug' : undefined
      };

      // Build command
      let command = 'ng test';
      
      if (config.singleRun) {
        command += ' --watch=false';
      }
      
      if (!config.coverage) {
        command += ' --code-coverage=false';
      }

      if (pattern) {
        command += ` --include="${pattern}"`;
      }

      // Execute command
      const child = exec(command, { 
        cwd: this.projectRoot,
        env: env 
      });

      let output = '';
      let errorOutput = '';

      child.stdout?.on('data', (data) => {
        output += data;
        if (!config.watch) {
          process.stdout.write(data);
        }
      });

      child.stderr?.on('data', (data) => {
        errorOutput += data;
        if (!config.watch) {
          process.stderr.write(data);
        }
      });

      child.on('close', (code) => {
        if (code === 0) {
          const results = this.parseTestResults(output);
          resolve(results);
        } else {
          reject(new Error(`Tests failed with exit code ${code}\n${errorOutput}`));
        }
      });

      child.on('error', (error) => {
        reject(error);
      });
    });
  }

  /**
   * Parse test results from output
   */
  private parseTestResults(output: string): TestResults {
    const lines = output.split('\n');
    
    // Default results
    const results: TestResults = {
      success: true,
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0
    };

    // Parse test summary
    for (const line of lines) {
      if (line.includes('TOTAL:')) {
        const match = line.match(/(\d+) SUCCESS/);
        if (match) {
          results.passed = parseInt(match[1]);
          results.total = results.passed;
        }
        
        const failMatch = line.match(/(\d+) FAILED/);
        if (failMatch) {
          results.failed = parseInt(failMatch[1]);
          results.total += results.failed;
          results.success = false;
        }
      }

      // Parse coverage summary
      if (line.includes('Statements') && line.includes('%')) {
        const match = line.match(/(\d+\.?\d*)%/);
        if (match && !results.coverage) {
          results.coverage = {
            statements: parseFloat(match[1]),
            branches: 0,
            functions: 0,
            lines: 0
          };
        }
      }
    }

    return results;
  }

  /**
   * Generate comprehensive test report
   */
  private async generateTestReport(results: TestResults): Promise<void> {
    const report = {
      timestamp: new Date().toISOString(),
      results: results,
      environment: 'frontend',
      framework: 'Angular + Jasmine + Karma',
      summary: {
        success: results.success,
        testsPassing: results.passed,
        testsTotal: results.total,
        coverageStatements: results.coverage?.statements || 0,
        coverageBranches: results.coverage?.branches || 0
      }
    };

    const reportPath = path.join(this.projectRoot, 'test-results.json');
    await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
    
    console.log(`\n📊 Test report generated: ${reportPath}`);
    
    // Display summary
    this.displayTestSummary(results);
  }

  /**
   * Generate CI-friendly report
   */
  private async generateCIReport(results: TestResults): Promise<void> {
    const ciReport = {
      success: results.success,
      total_tests: results.total,
      passed_tests: results.passed,
      failed_tests: results.failed,
      skipped_tests: results.skipped,
      coverage: results.coverage
    };

    const reportPath = path.join(this.projectRoot, 'ci-test-results.json');
    await fs.writeFile(reportPath, JSON.stringify(ciReport, null, 2));

    // Set exit code for CI
    if (!results.success) {
      process.exit(1);
    }
  }

  /**
   * Display test summary in console
   */
  private displayTestSummary(results: TestResults): void {
    console.log('\n' + '='.repeat(60));
    console.log('📋 FRONTEND TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`✅ Tests Passed: ${results.passed}`);
    console.log(`❌ Tests Failed: ${results.failed}`);
    console.log(`⏭️  Tests Skipped: ${results.skipped}`);
    console.log(`📊 Total Tests: ${results.total}`);
    console.log(`🎯 Success Rate: ${((results.passed / results.total) * 100).toFixed(1)}%`);
    
    if (results.coverage) {
      console.log('\n📈 COVERAGE SUMMARY:');
      console.log(`   Statements: ${results.coverage.statements.toFixed(1)}%`);
      console.log(`   Branches: ${results.coverage.branches.toFixed(1)}%`);
      console.log(`   Functions: ${results.coverage.functions.toFixed(1)}%`);
      console.log(`   Lines: ${results.coverage.lines.toFixed(1)}%`);
    }
    
    console.log('='.repeat(60) + '\n');
  }

  /**
   * Clean up test artifacts
   */
  async cleanup(): Promise<void> {
    try {
      await fs.rmdir(this.coverageDir, { recursive: true });
      console.log('🧹 Cleaned up test artifacts');
    } catch (error) {
      // Ignore cleanup errors
    }
  }
}

/**
 * CLI Interface
 */
async function main() {
  const runner = new FrontendTestRunner();
  const command = process.argv[2];

  try {
    switch (command) {
      case 'all':
        await runner.runAllTests();
        break;
        
      case 'watch':
        await runner.runWatchMode();
        break;
        
      case 'ci':
        await runner.runCITests();
        break;
        
      case 'unit':
        await runner.runTestSuite('**/*.spec.ts');
        break;
        
      case 'integration':
        await runner.runTestSuite('**/integration/**/*.spec.ts');
        break;
        
      case 'service':
        await runner.runTestSuite('**/services/**/*.spec.ts');
        break;
        
      case 'component':
        await runner.runTestSuite('**/components/**/*.spec.ts');
        break;
        
      case 'cleanup':
        await runner.cleanup();
        break;
        
      default:
        console.log('🧪 Frontend Test Runner');
        console.log('\nUsage: npm run test:frontend [command]\n');
        console.log('Available commands:');
        console.log('  all         - Run all tests');
        console.log('  watch       - Run tests in watch mode');
        console.log('  ci          - Run tests for CI environment');
        console.log('  unit        - Run only unit tests');
        console.log('  integration - Run only integration tests');
        console.log('  service     - Run only service tests');
        console.log('  component   - Run only component tests');
        console.log('  cleanup     - Clean up test artifacts');
        console.log('\nExamples:');
        console.log('  npm run test:frontend all');
        console.log('  npm run test:frontend watch');
        console.log('  npm run test:frontend ci');
        break;
    }
  } catch (error) {
    console.error('💥 Test runner failed:', error);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

export { FrontendTestRunner, TestConfig, TestResults };

