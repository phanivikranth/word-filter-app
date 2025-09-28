import { ComponentFixture } from '@angular/core/testing';
import { DebugElement } from '@angular/core';
import { By } from '@angular/platform-browser';
import { FormGroup, AbstractControl } from '@angular/forms';

/**
 * Test utilities for Angular component testing
 */

/**
 * Generic utility to get element by selector
 */
export function getElement<T>(
  fixture: ComponentFixture<T>, 
  selector: string
): HTMLElement | null {
  const debugElement = fixture.debugElement.query(By.css(selector));
  return debugElement ? debugElement.nativeElement : null;
}

/**
 * Get multiple elements by selector
 */
export function getElements<T>(
  fixture: ComponentFixture<T>, 
  selector: string
): HTMLElement[] {
  const debugElements = fixture.debugElement.queryAll(By.css(selector));
  return debugElements.map(de => de.nativeElement);
}

/**
 * Get element and expect it to exist
 */
export function expectElement<T>(
  fixture: ComponentFixture<T>, 
  selector: string
): HTMLElement {
  const element = getElement(fixture, selector);
  if (!element) {
    fail(`Expected element with selector "${selector}" to exist`);
  }
  return element!;
}

/**
 * Click an element by selector
 */
export function clickElement<T>(
  fixture: ComponentFixture<T>, 
  selector: string
): void {
  const element = expectElement(fixture, selector);
  element.click();
  fixture.detectChanges();
}

/**
 * Set input value and trigger input event
 */
export function setInputValue<T>(
  fixture: ComponentFixture<T>, 
  selector: string, 
  value: string
): void {
  const input = expectElement(fixture, selector) as HTMLInputElement;
  input.value = value;
  input.dispatchEvent(new Event('input'));
  fixture.detectChanges();
}

/**
 * Set input value and trigger change event
 */
export function setInputValueWithChange<T>(
  fixture: ComponentFixture<T>, 
  selector: string, 
  value: string
): void {
  const input = expectElement(fixture, selector) as HTMLInputElement;
  input.value = value;
  input.dispatchEvent(new Event('input'));
  input.dispatchEvent(new Event('change'));
  fixture.detectChanges();
}

/**
 * Get text content of element
 */
export function getTextContent<T>(
  fixture: ComponentFixture<T>, 
  selector: string
): string {
  const element = expectElement(fixture, selector);
  return element.textContent?.trim() || '';
}

/**
 * Check if element exists
 */
export function hasElement<T>(
  fixture: ComponentFixture<T>, 
  selector: string
): boolean {
  return getElement(fixture, selector) !== null;
}

/**
 * Check if element is visible
 */
export function isElementVisible<T>(
  fixture: ComponentFixture<T>, 
  selector: string
): boolean {
  const element = getElement(fixture, selector);
  if (!element) return false;
  
  const style = window.getComputedStyle(element);
  return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
}

/**
 * Wait for element to appear
 */
export async function waitForElement<T>(
  fixture: ComponentFixture<T>, 
  selector: string, 
  timeout: number = 3000
): Promise<HTMLElement> {
  const start = Date.now();
  
  while (Date.now() - start < timeout) {
    const element = getElement(fixture, selector);
    if (element) {
      return element;
    }
    
    fixture.detectChanges();
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  
  throw new Error(`Element with selector "${selector}" did not appear within ${timeout}ms`);
}

/**
 * Form testing utilities
 */
export class FormTestHelper {
  constructor(private form: FormGroup) {}

  /**
   * Set multiple form values at once
   */
  setValues(values: { [key: string]: any }): void {
    this.form.patchValue(values);
  }

  /**
   * Get form control value
   */
  getValue(controlName: string): any {
    return this.form.get(controlName)?.value;
  }

  /**
   * Set form control value
   */
  setValue(controlName: string, value: any): void {
    const control = this.form.get(controlName);
    if (control) {
      control.setValue(value);
    }
  }

  /**
   * Check if form control is valid
   */
  isValid(controlName: string): boolean {
    return this.form.get(controlName)?.valid ?? false;
  }

  /**
   * Check if form control has error
   */
  hasError(controlName: string, errorType: string): boolean {
    const control = this.form.get(controlName);
    return control?.hasError(errorType) ?? false;
  }

  /**
   * Get form control errors
   */
  getErrors(controlName: string): any {
    return this.form.get(controlName)?.errors;
  }

  /**
   * Reset form to default values
   */
  reset(value?: any): void {
    this.form.reset(value);
  }

  /**
   * Check if entire form is valid
   */
  isFormValid(): boolean {
    return this.form.valid;
  }

  /**
   * Mark all form controls as touched
   */
  markAllAsTouched(): void {
    this.form.markAllAsTouched();
  }
}

/**
 * Create a form test helper
 */
export function createFormTestHelper(form: FormGroup): FormTestHelper {
  return new FormTestHelper(form);
}

/**
 * Async testing utilities
 */
export class AsyncTestHelper {
  /**
   * Wait for async operation to complete
   */
  static async waitFor(
    condition: () => boolean, 
    timeout: number = 3000
  ): Promise<void> {
    const start = Date.now();
    
    while (Date.now() - start < timeout) {
      if (condition()) {
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    
    throw new Error(`Condition not met within ${timeout}ms`);
  }

  /**
   * Wait for component property to change
   */
  static async waitForPropertyChange<T, K extends keyof T>(
    component: T,
    property: K,
    expectedValue: T[K],
    timeout: number = 3000
  ): Promise<void> {
    await this.waitFor(() => component[property] === expectedValue, timeout);
  }

  /**
   * Wait for component property to be truthy
   */
  static async waitForPropertyTruthy<T, K extends keyof T>(
    component: T,
    property: K,
    timeout: number = 3000
  ): Promise<void> {
    await this.waitFor(() => !!component[property], timeout);
  }

  /**
   * Wait for component property to be falsy
   */
  static async waitForPropertyFalsy<T, K extends keyof T>(
    component: T,
    property: K,
    timeout: number = 3000
  ): Promise<void> {
    await this.waitFor(() => !component[property], timeout);
  }
}

/**
 * Spy utilities for easier mocking
 */
export class SpyHelper {
  /**
   * Create spy object with methods
   */
  static createSpyObj<T>(
    baseName: string, 
    methods: string[], 
    properties?: { [key: string]: any }
  ): jasmine.SpyObj<T> {
    const spy = jasmine.createSpyObj(baseName, methods, properties);
    return spy;
  }

  /**
   * Create property spy for 'get' access
   */
  static spyOnPropertyGet(
    object: any, 
    property: string
  ): jasmine.Spy {
    return spyOnProperty(object, property, 'get');
  }

  /**
   * Create property spy for 'set' access
   */
  static spyOnPropertySet(
    object: any, 
    property: string
  ): jasmine.Spy {
    return spyOnProperty(object, property, 'set');
  }

  /**
   * Create method spy with return value
   */
  static spyOnWithReturnValue(
    object: any, 
    method: string, 
    returnValue: any
  ): jasmine.Spy {
    return spyOn(object, method).and.returnValue(returnValue);
  }

  /**
   * Create method spy that calls through
   */
  static spyOnAndCallThrough(
    object: any, 
    method: string
  ): jasmine.Spy {
    return spyOn(object, method).and.callThrough();
  }
}

/**
 * Error testing utilities
 */
export class ErrorTestHelper {
  /**
   * Expect function to throw error
   */
  static expectToThrow(fn: () => any, expectedError?: string | RegExp): void {
    expect(fn).toThrow(expectedError);
  }

  /**
   * Expect async function to throw error
   */
  static async expectAsyncToThrow(
    fn: () => Promise<any>, 
    expectedError?: string | RegExp
  ): Promise<void> {
    let error: any;
    try {
      await fn();
    } catch (e) {
      error = e;
    }
    
    if (!error) {
      fail('Expected function to throw error');
    }
    
    if (expectedError) {
      if (typeof expectedError === 'string') {
        expect(error.message).toContain(expectedError);
      } else {
        expect(error.message).toMatch(expectedError);
      }
    }
  }

  /**
   * Create mock error with status
   */
  static createHttpError(status: number, message: string): any {
    return {
      status: status,
      statusText: message,
      message: message,
      name: 'HttpErrorResponse'
    };
  }
}

/**
 * Component state testing utilities
 */
export class ComponentStateHelper<T> {
  constructor(private component: T, private fixture: ComponentFixture<T>) {}

  /**
   * Set component property and detect changes
   */
  setProperty<K extends keyof T>(property: K, value: T[K]): void {
    this.component[property] = value;
    this.fixture.detectChanges();
  }

  /**
   * Set multiple properties and detect changes
   */
  setProperties(properties: Partial<T>): void {
    Object.assign(this.component as any, properties);
    this.fixture.detectChanges();
  }

  /**
   * Get component property value
   */
  getProperty<K extends keyof T>(property: K): T[K] {
    return this.component[property];
  }

  /**
   * Check if component has property
   */
  hasProperty(property: string): boolean {
    return property in (this.component as any);
  }

  /**
   * Trigger component method and detect changes
   */
  callMethod(methodName: string, ...args: any[]): any {
    const method = (this.component as any)[methodName];
    if (typeof method === 'function') {
      const result = method.apply(this.component, args);
      this.fixture.detectChanges();
      return result;
    }
    throw new Error(`Method ${methodName} is not a function`);
  }
}

/**
 * Create component state helper
 */
export function createComponentStateHelper<T>(
  component: T, 
  fixture: ComponentFixture<T>
): ComponentStateHelper<T> {
  return new ComponentStateHelper(component, fixture);
}

/**
 * Custom matchers for better assertions
 */
declare global {
  namespace jasmine {
    interface Matchers<T> {
      toHaveClass(className: string): boolean;
      toBeVisible(): boolean;
      toHaveText(text: string): boolean;
      toContainText(text: string): boolean;
    }
  }
}

/**
 * Add custom matchers
 */
export function addCustomMatchers(): void {
  beforeEach(() => {
    jasmine.addMatchers({
      toHaveClass: () => ({
        compare: (actual: HTMLElement, className: string) => {
          const result = {
            pass: actual.classList.contains(className),
            message: ''
          };
          
          if (result.pass) {
            result.message = `Expected element not to have class '${className}'`;
          } else {
            result.message = `Expected element to have class '${className}'`;
          }
          
          return result;
        }
      }),
      
      toBeVisible: () => ({
        compare: (actual: HTMLElement) => {
          const style = window.getComputedStyle(actual);
          const result = {
            pass: style.display !== 'none' && 
                  style.visibility !== 'hidden' && 
                  style.opacity !== '0',
            message: ''
          };
          
          if (result.pass) {
            result.message = 'Expected element not to be visible';
          } else {
            result.message = 'Expected element to be visible';
          }
          
          return result;
        }
      }),
      
      toHaveText: () => ({
        compare: (actual: HTMLElement, text: string) => {
          const actualText = actual.textContent?.trim() || '';
          const result = {
            pass: actualText === text,
            message: ''
          };
          
          if (result.pass) {
            result.message = `Expected element not to have text '${text}'`;
          } else {
            result.message = `Expected element to have text '${text}', but got '${actualText}'`;
          }
          
          return result;
        }
      }),
      
      toContainText: () => ({
        compare: (actual: HTMLElement, text: string) => {
          const actualText = actual.textContent?.trim() || '';
          const result = {
            pass: actualText.includes(text),
            message: ''
          };
          
          if (result.pass) {
            result.message = `Expected element not to contain text '${text}'`;
          } else {
            result.message = `Expected element to contain text '${text}', but got '${actualText}'`;
          }
          
          return result;
        }
      })
    });
  });
}
