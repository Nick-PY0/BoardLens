#import <Cocoa/Cocoa.h>
#import <CommonCrypto/CommonDigest.h>
#import <unistd.h>

static NSString *digest(NSString *path) {
    NSInputStream *input=[NSInputStream inputStreamWithFileAtPath:path];[input open];
    CC_SHA256_CTX context;CC_SHA256_Init(&context);uint8_t buffer[65536];NSInteger n;
    while((n=[input read:buffer maxLength:sizeof(buffer)])>0)CC_SHA256_Update(&context,buffer,(CC_LONG)n);
    [input close];if(n<0)@throw [NSException exceptionWithName:@"Read" reason:@"Could not read the application package." userInfo:nil];
    unsigned char hash[CC_SHA256_DIGEST_LENGTH];CC_SHA256_Final(hash,&context);NSMutableString *result=[NSMutableString string];for(int i=0;i<sizeof(hash);i++)[result appendFormat:@"%02x",hash[i]];return result;
}
static void fail(NSString *message) {NSAlert *alert=[NSAlert new];alert.messageText=@"BoardLens could not start";alert.informativeText=message;[alert runModal];[NSApp terminate:nil];}
int main(int argc,const char *argv[]) {
    @autoreleasepool {
        [NSApplication sharedApplication];[NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
        NSString *resources=NSBundle.mainBundle.resourcePath;
        NSDictionary *meta=[NSJSONSerialization JSONObjectWithData:[NSData dataWithContentsOfFile:[resources stringByAppendingPathComponent:@"metadata.json"]] options:0 error:nil];
        if(!meta){fail(@"The app package is incomplete. Download the complete Mac app again.");return 1;}
        NSString *base=[NSHomeDirectory() stringByAppendingPathComponent:@"Library/Application Support/BoardLens/native"];
        NSString *key=meta[@"payload_sha256"],*target=[[base stringByAppendingPathComponent:@"packages"] stringByAppendingPathComponent:[key substringToIndex:20]];
        NSString *smoke=nil;for(int i=1;i+1<argc;i++)if(strcmp(argv[i],"--self-test")==0)smoke=[NSString stringWithUTF8String:argv[i+1]];
        NSWindow *window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,420,130) styleMask:NSWindowStyleMaskTitled backing:NSBackingStoreBuffered defer:NO];window.title=@"BoardLens";[window center];
        NSTextField *label=[NSTextField labelWithString:@"Preparing BoardLens…"];label.font=[NSFont systemFontOfSize:17 weight:NSFontWeightMedium];label.frame=NSMakeRect(28,74,370,26);[window.contentView addSubview:label];
        NSProgressIndicator *progress=[[NSProgressIndicator alloc] initWithFrame:NSMakeRect(28,38,364,18)];progress.style=NSProgressIndicatorStyleBar;progress.indeterminate=YES;[progress startAnimation:nil];[window.contentView addSubview:progress];
        if(![[NSFileManager defaultManager] fileExistsAtPath:[target stringByAppendingPathComponent:@".ready"]]){[window makeKeyAndOrderFront:nil];[NSApp activateIgnoringOtherApps:YES];}
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
            @try {
                NSFileManager *files=NSFileManager.defaultManager;
                if(![files fileExistsAtPath:[target stringByAppendingPathComponent:@".ready"]]){
                    NSString *payload=[resources stringByAppendingPathComponent:@"payload.zip"];
                    if(![digest(payload) isEqualToString:key])@throw [NSException exceptionWithName:@"Checksum" reason:@"The application package checksum did not match. Download a fresh copy." userInfo:nil];
                    NSString *stage=[[base stringByAppendingPathComponent:@"packages"] stringByAppendingPathComponent:[@"stage-" stringByAppendingString:NSUUID.UUID.UUIDString]];
                    [files createDirectoryAtPath:stage withIntermediateDirectories:YES attributes:nil error:nil];
                    NSTask *extract=[NSTask new];extract.executableURL=[NSURL fileURLWithPath:@"/usr/bin/ditto"];extract.arguments=@[@"-xk",payload,stage];extract.standardOutput=NSFileHandle.fileHandleWithNullDevice;extract.standardError=NSFileHandle.fileHandleWithNullDevice;
                    NSError *error=nil;if(![extract launchAndReturnError:&error])@throw [NSException exceptionWithName:@"Extract" reason:error.localizedDescription userInfo:nil];[extract waitUntilExit];if(extract.terminationStatus)@throw [NSException exceptionWithName:@"Extract" reason:@"Could not prepare the bundled runtime." userInfo:nil];
                    [@"ready" writeToFile:[stage stringByAppendingPathComponent:@".ready"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
                    if(![files moveItemAtPath:stage toPath:target error:&error]){if([files fileExistsAtPath:[target stringByAppendingPathComponent:@".ready"]])[files removeItemAtPath:stage error:nil];else @throw [NSException exceptionWithName:@"Install" reason:error.localizedDescription userInfo:nil];}
                }
                dispatch_async(dispatch_get_main_queue(),^{
                    NSString *logs=[base stringByAppendingPathComponent:@"logs"];[NSFileManager.defaultManager createDirectoryAtPath:logs withIntermediateDirectories:YES attributes:nil error:nil];NSString *log=[logs stringByAppendingPathComponent:@"latest.log"];
                    freopen(log.fileSystemRepresentation,"a",stdout);freopen(log.fileSystemRepresentation,"a",stderr);
                    unsetenv("PYTHONHOME");unsetenv("PYTHONPATH");unsetenv("VIRTUAL_ENV");unsetenv("__PYVENV_LAUNCHER__");setenv("BOARDLENS_NATIVE_DATA",base.fileSystemRepresentation,1);
                    if(smoke){setenv("BOARDLENS_NATIVE_SMOKE",smoke.fileSystemRepresentation,1);NSString *data=[[smoke stringByDeletingLastPathComponent] stringByAppendingPathComponent:@"smoke-data"];setenv("BOARDLENS_DATA_DIR",data.fileSystemRepresentation,1);setenv("BOARDLENS_TEST_MODE","1",1);setenv("PYNPUT_BACKEND","dummy",1);if(!getenv("BOARDLENS_VISIBLE_TEST"))setenv("QT_QPA_PLATFORM","offscreen",1);}
                    NSString *python=[target stringByAppendingPathComponent:@"runtime/bin/python3"],*script=[target stringByAppendingPathComponent:@"start.py"];
                    const char *args[]={python.fileSystemRepresentation,script.fileSystemRepresentation,NULL};execv(args[0],(char *const *)args);fail(@"Could not open the bundled Python runtime. See Library/Application Support/BoardLens/native/logs/latest.log.");
                });
            } @catch(NSException *error){dispatch_async(dispatch_get_main_queue(),^{fail(error.reason);});}
        });
        [NSApp run];return 0;
    }
}
