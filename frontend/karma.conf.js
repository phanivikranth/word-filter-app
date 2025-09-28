// Karma configuration file, see link for more information
// https://karma-runner.github.io/1.0/config/configuration-file.html

module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('karma-coverage'),
      require('@angular-devkit/build-angular/plugins/karma')
    ],
    client: {
      jasmine: {
        // you can add configuration options for Jasmine here
        // the possible options are listed at https://jasmine.github.io/api/edge/Configuration.html
        // for example, you can disable the random execution order
        random: false,
        stopSpecOnExpectationFailure: false
      },
      clearContext: false // leave Jasmine Spec Runner output visible in browser
    },
    jasmineHtmlReporter: {
      suppressAll: true // removes the duplicated traces
    },
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/word-filter-frontend'),
      subdir: '.',
      reporters: [
        { type: 'html' },
        { type: 'text-summary' },
        { type: 'lcov' },
        { type: 'json-summary' }
      ],
      check: {
        global: {
          statements: 80,
          branches: 70,
          functions: 80,
          lines: 80
        }
      },
      watermarks: {
        statements: [50, 75],
        functions: [50, 75],
        branches: [50, 75],
        lines: [50, 75]
      }
    },
    reporters: ['progress', 'kjhtml', 'coverage'],
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    browsers: ['Chrome'],
    singleRun: false,
    restartOnFileChange: true,
    
    // Performance optimizations
    browserNoActivityTimeout: 60000,
    browserDisconnectTimeout: 10000,
    browserDisconnectTolerance: 3,
    captureTimeout: 60000,
    
    // Custom configurations for different environments
    customLaunchers: {
      ChromeHeadlessCI: {
        base: 'ChromeHeadless',
        flags: [
          '--no-sandbox',
          '--disable-web-security',
          '--disable-gpu',
          '--disable-dev-shm-usage',
          '--memory-pressure-off',
          '--max_old_space_size=4096'
        ]
      },
      ChromeDebug: {
        base: 'Chrome',
        flags: ['--remote-debugging-port=9333'],
        debug: true
      },
      ChromeHeadlessLocal: {
        base: 'ChromeHeadless',
        flags: [
          '--disable-web-security',
          '--disable-features=VizDisplayCompositor'
        ]
      }
    },

    // File patterns for different test types
    files: [
      // Add any global test setup files here if needed
    ],

    // Preprocessors
    preprocessors: {
      // Source files for coverage
      'src/**/*.ts': ['coverage']
    },

    // MIME type configuration
    mime: {
      'text/x-typescript': ['ts','tsx']
    }
  });

  // Environment-specific configurations
  if (process.env.CI) {
    // CI environment configuration
    config.set({
      browsers: ['ChromeHeadlessCI'],
      singleRun: true,
      autoWatch: false,
      reporters: ['progress', 'coverage'],
      coverageReporter: {
        ...config.coverageReporter,
        reporters: [
          { type: 'lcov' },
          { type: 'text-summary' },
          { type: 'cobertura' },
          { type: 'json-summary' }
        ]
      }
    });
  }

  // Development environment with debugging
  if (process.env.NODE_ENV === 'debug') {
    config.set({
      browsers: ['ChromeDebug'],
      singleRun: false,
      autoWatch: true,
      reporters: ['progress', 'kjhtml']
    });
  }

  // Headless mode for local development
  if (process.env.HEADLESS) {
    config.set({
      browsers: ['ChromeHeadlessLocal'],
      singleRun: true,
      autoWatch: false
    });
  }

  // Test performance configuration
  if (process.env.TEST_PERFORMANCE) {
    config.set({
      client: {
        jasmine: {
          random: false,
          stopSpecOnExpectationFailure: true,
          failFast: true
        }
      },
      reporters: ['progress', 'time'],
      timeReporter: {
        reportType: 'json',
        outputFile: 'test-performance.json'
      }
    });
  }
};

