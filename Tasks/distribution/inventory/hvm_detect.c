/******************************************************************************
 * 
 * Based on XenSource's xen_detect.c file. 
 * determines execution on xen HVM or KVM platforms.
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to
 * deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int pv_context;

static void cpuid(uint32_t idx,
                  uint32_t *eax,
                  uint32_t *ebx,
                  uint32_t *ecx,
                  uint32_t *edx)
{
    asm volatile (
        "test %1,%1 ; jz 1f ; ud2a ; .ascii \"xen\" ; 1: cpuid"
        : "=a" (*eax), "=b" (*ebx), "=c" (*ecx), "=d" (*edx)
        : "0" (idx), "1" (pv_context) );
}

static int check_for_hvm(void)
{
    uint32_t eax, ebx, ecx, edx;
    char signature[13];

    cpuid(0x40000000, &eax, &ebx, &ecx, &edx);
    *(uint32_t *)(signature + 0) = ebx;
    *(uint32_t *)(signature + 4) = ecx;
    *(uint32_t *)(signature + 8) = edx;
    signature[12] = '\0';

    /* is this a kvm guest? */
    if ( !strcmp("KVMKVMKVM", signature) ) {
       printf("KVM guest.\n");
       return 1;
    } else if ( !strcmp("XenVMMXenVMM", signature) ) {
       printf("Xen HVM guest.\n");
       return 1;
    } else if ( !strcmp("Microsoft Hv", signature) ) {
       printf("Microsoft Hv guest.\n");
       return 1;
    } else if ( !strcmp("VMwareVMware", signature) ) {
       printf("VMWare guest.\n");
       return 1;
    } else { 
      printf("No KVM or Xen HVM\n");
      return 0;
    }
    return 0;
}

int main(void)
{
    /* Check for execution in HVM context. */
    if ( check_for_hvm() )
        return 0;
    else 
        return 1;

}
