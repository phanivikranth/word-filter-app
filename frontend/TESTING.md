# Frontend Testing Guide

## Overview

The Word Filter Frontend uses a comprehensive testing strategy built on **Angular Testing Utilities**, **Jasmine**, and **Karma** to ensure robust functionality and maintainability.

## Testing Framework

- **Jasmine**: Testing framework for behavior-driven development
- **Karma**: Test runner for executing tests in real browsers  
- **Angular Testing Utilities**: Specialized testing tools for Angular components
- **HttpClientTestingModule**: Mock HTTP requests for service testing

## Test Structure

### 📁 Test Files Organization

```
src/
├── app/
│   ├── services/
│   │   ├── word.service.ts
│   │   └── word.service.spec.ts
│   ├── app.component.ts
│   ├── app.component.spec.ts
│   ├── integration/
│   │   └── app-integration.spec.ts
│   └── testing/
│       ├── test-data.ts
│       └── test-utils.ts
├── test-runner.ts
└── karma.conf.js
```

## Test Categories

### 1. 🔧 **Service Tests** (`*.service.spec.ts`)
Tests for the `WordService` covering:
- HTTP request mocking with `HttpTestingController`
- API endpoint validation
- Error handling scenarios
- Observable stream testing
- Parameter validation

**Example:**
```typescript
it('should fetch filtered words with all parameters', () => {
  const filter: WordFilter = { contains: 'app', min_length: 3 };
  
  service.getFilteredWords(filter).subscribe(words => {
    expect(words).toEqual(['apple', 'application']);
  });
  
  const req = httpMock.expectOne(req => 
    req.url.includes('/words') && 
    req.params.get('contains') === 'app'
  );
  req.flush(['apple', 'application']);
});
```

### 2. 🎯 **Component Tests** (`*.component.spec.ts`)
Tests for `AppComponent` covering:
- Form validation and reactive forms
- Component state management
- User interaction handling
- Tab switching functionality
- Error state management
- Loading state management

**Example:**
```typescript
it('should validate basic search input', () => {
  component.basicSearchTerm = 'invalid123';
  
  component.searchBasicWord();
  
  expect(component.basicSearchError).toBe('Word must contain only letters.');
  expect(wordService.searchBasicWord).not.toHaveBeenCalled();
});
```

### 3. 🔗 **Integration Tests** (`integration/*.spec.ts`)
End-to-end workflow tests covering:
- Component-service interaction
- Complete user workflows
- Real HTTP request/response cycles
- Error handling across layers
- State synchronization

**Example:**
```typescript
it('should complete basic search to word addition workflow', async () => {
  // User searches for word not in collection
  component.basicSearchTerm = 'newword';
  component.searchBasicWord();
  
  // Mock API responses
  const checkReq = httpMock.expectOne('/words/check');
  checkReq.flush({ exists: false });
  
  // User adds word and system refreshes
  component.addWordToCollection('newword');
  // ... verify complete workflow
});
```

## Test Data and Utilities

### 📊 **Test Data** (`testing/test-data.ts`)
Centralized mock data including:
- `MOCK_WORD_STATS`: Sample word statistics
- `MOCK_WORDS_LIST`: Sample word arrays
- `MOCK_BASIC_SEARCH_RESULT`: Search result objects
- `TEST_SCENARIOS`: Predefined test cases
- Helper functions for creating mock objects

### 🛠️ **Test Utilities** (`testing/test-utils.ts`)
Reusable testing utilities:
- `getElement()`, `clickElement()`, `setInputValue()`: DOM interaction helpers
- `FormTestHelper`: Form testing utilities
- `AsyncTestHelper`: Async operation testing
- `SpyHelper`: Enhanced spy creation
- `ComponentStateHelper`: Component state management
- Custom Jasmine matchers

## Running Tests

### Basic Commands

```bash
# Run all tests
npm test

# Run all tests with coverage
npm run test:all

# Run tests in watch mode  
npm run test:watch

# Run tests in CI mode
npm run test:ci

# Run tests headless (faster)
npm run test:headless
```

### Specific Test Categories

```bash
# Run only service tests
npm run test:service

# Run only component tests  
npm run test:component

# Run only integration tests
npm run test:integration

# Run only unit tests
npm run test:unit
```

### Advanced Testing

```bash
# Run with coverage and open report
npm run test:coverage

# Debug mode with browser debugging
npm run test:debug

# Custom test runner
npm run test:runner all
```

## Test Configuration

### Karma Configuration (`karma.conf.js`)

- **Development**: Chrome browser with live reload
- **CI**: Headless Chrome for continuous integration
- **Debug**: Chrome with remote debugging enabled
- **Coverage**: Code coverage reporting with multiple formats

### Environment-Specific Settings

- **CI Environment**: `ChromeHeadlessCI` with optimized flags
- **Local Development**: `Chrome` with debugging tools
- **Headless Testing**: `ChromeHeadlessLocal` for faster feedback

## Coverage Targets

Our testing aims for:
- **Statements**: 80%+ coverage
- **Branches**: 70%+ coverage  
- **Functions**: 80%+ coverage
- **Lines**: 80%+ coverage

## Best Practices

### 1. **Test Structure**
```typescript
describe('ComponentName', () => {
  let component: ComponentName;
  let fixture: ComponentFixture<ComponentName>;
  
  beforeEach(async () => {
    // Test setup
  });
  
  describe('Feature Group', () => {
    it('should perform specific behavior', () => {
      // Arrange, Act, Assert
    });
  });
});
```

### 2. **Mock Services**
```typescript
const mockService = jasmine.createSpyObj('ServiceName', ['method1', 'method2']);
mockService.method1.and.returnValue(of(mockData));
```

### 3. **Async Testing**
```typescript
it('should handle async operations', async () => {
  component.performAsyncOperation();
  
  await AsyncTestHelper.waitForPropertyChange(component, 'loading', false);
  
  expect(component.result).toBeTruthy();
});
```

### 4. **Error Testing**
```typescript
it('should handle service errors', () => {
  service.getData.and.returnValue(throwError(() => new Error('API Error')));
  
  component.loadData();
  
  expect(component.error).toBe('Failed to load data');
});
```

## Common Testing Patterns

### Form Testing
```typescript
const formHelper = createFormTestHelper(component.filterForm);
formHelper.setValues({ contains: 'test', limit: 50 });
expect(formHelper.isFormValid()).toBeTruthy();
```

### HTTP Testing
```typescript
service.getData().subscribe(result => {
  expect(result).toEqual(expectedData);
});

const req = httpMock.expectOne('/api/data');
expect(req.request.method).toBe('GET');
req.flush(expectedData);
```

### Component State Testing
```typescript
const stateHelper = createComponentStateHelper(component, fixture);
stateHelper.setProperty('activeTab', 'search');
expect(stateHelper.getProperty('activeTab')).toBe('search');
```

## Debugging Tests

### Browser Debugging
```bash
npm run test:debug
# Opens Chrome with debugging tools at localhost:9876
```

### Console Output
```typescript
it('should debug test', () => {
  console.log('Component state:', component);
  console.log('Form value:', component.form.value);
  
  // Add breakpoints in browser dev tools
  debugger;
  
  expect(component.property).toBeTruthy();
});
```

## Continuous Integration

The test suite is configured for CI environments with:
- Headless browser execution
- Coverage reporting in multiple formats (LCOV, JSON, XML)
- JUnit XML output for build systems
- Fail-fast execution for quick feedback

## Performance Considerations

- **Parallel execution**: Tests run in parallel when possible
- **Selective testing**: Run specific test suites during development
- **Mocked dependencies**: All external dependencies are mocked
- **Optimized browser configuration**: Headless mode with performance flags

## Troubleshooting

### Common Issues

1. **Tests timeout**: Increase `browserNoActivityTimeout` in karma.conf.js
2. **Memory issues**: Add `--max_old_space_size=4096` to Chrome flags
3. **HTTP errors**: Verify all HTTP requests are mocked in `afterEach(httpMock.verify())`
4. **Async timing**: Use `AsyncTestHelper.waitFor()` for timing-sensitive tests

### Test Debugging

```typescript
// Log component state
console.log('Component:', JSON.stringify(component, null, 2));

// Log form state  
console.log('Form valid:', component.form.valid);
console.log('Form errors:', component.form.errors);

// Log service calls
expect(mockService.method).toHaveBeenCalledWith(expectedArgs);
```

---

## 🎯 Testing Philosophy

Our testing strategy follows the **Testing Pyramid**:
- **Unit Tests (70%)**: Fast, isolated tests for individual components/services
- **Integration Tests (20%)**: Component-service interaction tests
- **E2E Tests (10%)**: Full user workflow tests (future implementation)

This ensures comprehensive coverage while maintaining fast feedback loops and reliable test execution.

