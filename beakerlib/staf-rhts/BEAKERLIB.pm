#############################################################################
# Ray Chen <chenrano2002@163.com>
#
# This software is licensed under the Eclipse Public License (EPL) V1.0.    #
#############################################################################

package BEAKERLIB;

use PLSTAFService;
use PLSTAF;
use STAFLog;
use 5.008;
use threads;
use threads::shared;
use Thread::Queue;
use Data::Dumper;

use strict;
use warnings;

use constant kBEAKERLIBInvalidNumber => scalar 4001;
use constant kVersion => scalar "0.0.2";

# In this queue the master threads queue jobs for the slave worker
my $work_queue = new Thread::Queue;
my $free_workers : shared = 0;

# passed in part of parms
our $fServiceName;
# staf handle for service
our $fHandle;
our $fAddParser; 
our $fListParser;
our $fLineSep;
our $fLogHandle;

# Lists of BEAKERLIB funtions
our %BEAKERLIB = (
    "Journalling"   => ["rlJournalStart", "rlJournalEnd",
                        "rlJournalPrint", "rlJournalPrintText"],
    "Logging"       => ["rlLog", "rlLogDebug", "rlLogInfo",
                        "rlLogWarning", "rlLogError", "rlLogFatal",
                        "rlDie", "rlBundleLogs"],
    "Info"          => ["rlShowPackageVersion", "rlShowRunningKernel"], 
    "Phases"        => ["rlPhaseStart", "rlPhaseEnd", "rlPhaseStartSetup",
                        "rlPhaseStartTest", "rlPhaseStartCleanup"],
    "Metric"        => ["rlLogMetricLow", "rlLogMetricHigh"],
    "Rpm Handling"  => ["rlCheckRpm"],
    "Mounting"      => ["rlMount", "rlCheckMount", "rlAssertMount"],
    "Services"      => ["rlServiceStart", "rlServiceStop", "rlServiceRestore"],
    "Analyze"       => ["rlDejaSum"],
    "Time_Performance"  => ["rlPerfTime_RunsInTime", "rlPerfTime_AvgFromRuns"],
    "Backup_Restore"    => ["rlFileBackup", "rlFileRestore"],
    "Run_Watch_Report"  => ["rlRun", "rlWatchdog", "rlReport"],
    "Arithmetic_Asserts"=> ["rlAssert0", "lAssertEquals", 
                            "lAssertNotEquals", "rlAssertGreater",
                            "rlAssertGreaterOrEqual"],
    "File_Asserts"      => ["rlAssertExists", "rlAssertNotExists",
                            "rlAssertGrep", "rlAssertNotGrep"],
    "Virtual_XServer"   => ["rlVirtualXStart", "rlVirtualXStop",
                            "rlVirtualXGetDisplay"],
);

#sub Construct
#{
#    my $result = $fLogHandle->log("DEBUG", "Enter Construct function");
#}

sub new
{
    my ($class, $info) = @_;

    my $self =
    {
        threads_list => [],
        worker_created => 0,
        max_workers => 5, # do not create more than 5 workers
    };

    # Here, %info = ( ServiceTyp  => "the type of service", 
    #                 ServiceName => "name",
    #                 Params      => "parameters that have been passed to the 
    #                                 service (via the PARMS option)",
    #               WriteLocation => "The name of the root directory where the service 
    #                                 should write all service-related data (if it has any)",
    #              )

    $fServiceName = $info->{ServiceName};

    $fHandle = STAF::STAFHandle->new("STAF/Service/" . $fServiceName);

    # Load Log service
    $fLogHandle = STAF::STAFLog->new($fHandle, "beakerlib","GLOBAL", "INFO");
    $fLogHandle->log("DEBUG", "Enter new function");

    # Add Parser
    #$fAddParser = STAFCommandParser->new();

    # LIST parser
    $fListParser = STAFCommandParser->new();
    $fListParser->addOption("LIST", 1, STAFCommandParser::VALUENOTALLOWED);

    my $lineSepResult = $fHandle->submit2($STAF::STAFHandle::kReqSync,
        "local", "var", "resolve string {STAF/Config/Sep/Line}");

    $fLineSep = $lineSepResult->{result};

    return bless $self, $class;
}

#The service is active and ready to accept requests 
sub AcceptRequest
{
    my ($self, $info) = @_;
    my %hash : shared = %$info;

    #print_dump($fLogHandle, "self", $self);
    #print_dump($fLogHandle, "RequestHash", \%hash);

    if ($free_workers <= 0 and
        $self->{worker_created} < $self->{max_workers})
    {
        my $thr = threads->create(\&Worker);
        push @{ $self->{threads_list} }, $thr;
        $self->{worker_created}++;
    }
    else
    {
        lock $free_workers;
        $free_workers--;
    }

    $work_queue->enqueue(\%hash);

    return $STAF::DelayedAnswer;
}

# service worker to do staff actually.
sub Worker
{
    my $loop_flag = 1;

    while ($loop_flag)
    {
        eval
        {
            # get the work from the queue
            my $hash_ref = $work_queue->dequeue();

            if (not ref($hash_ref) and $hash_ref->{request} eq 'stop')
            {
                $loop_flag = 0;
                return;
            }

            my ($rc, $result) = handleRequest($hash_ref);

            STAF::DelayedAnswer($hash_ref->{requestNumber}, $rc, $result);

            # increase the number of free threads
            {
                lock $free_workers;
                $free_workers++;
            }
        }
    }

    return 1;
}

# Handle request from commands.
sub handleRequest
{
    my $info = shift;

    print_dump($fLogHandle, "RequestInfo", $info);

    my $lowerRequest = lc($info->{request});
    my $requestType = "";

    # get first "word" in request
    if($lowerRequest =~ m/\b(\w*)\b/)
    {
        $requestType = $&;
    }
    else
    {
        return (STAFResult::kInvalidRequestString,
            "Unknown DeviceService Request: " . ($info->{request}));
    }

    if ($requestType eq "list")
    {
        return handleList($info);
    }
    elsif ($requestType eq "query")
    {
        #return handleQuery($info);
    }
    elsif ($requestType eq "help")
    {
        return handleHelp();
    }
    elsif ($requestType eq "version")
    {
        return handleVersion();
    }
    else
    {
        return (STAFResult::kInvalidRequestString,
            "Unknown DeviceService Request: " . $info->{request});
    }

    return (0, "");
}

sub handleList
{
    my $info = shift;

    if($info->{trustLevel} < 2)
    {
        return (STAFResult::kAccessDenied,
                "Trust level 2 required for LIST request. Requesting " .
                "machine's trust level: " .  $info->{trustLevel});
    }

    my $result = (STAFResult::kOk, "");
    my $resultString = "";    

    # parse request
    my $parsedRequest = $fListParser->parse($info->{request});

    # check result of parse
    if ($parsedRequest->{rc} != STAFResult::kOk)
    {
        return (STAFResult::kInvalidRequestString,
            $parsedRequest->{errorBuffer});
    }

    # create a marshalling context with testList and one map class definition

    #print_dump($fLogHandle, "parsedRequest", $parsedRequest);

    $resultString = "List BEAKERLIB Function" . $fLineSep;
    foreach my $key ( keys %BEAKERLIB ) {
        my $group = $BEAKERLIB{$key};

        $resultString .= "$key\t\t";
        foreach my $function ( @$group ) {
            $resultString .= "$function ";
        }

        $resultString .= "$fLineSep";
    }

    return (STAFResult::kOk, $resultString);
}

sub handleVersion
{
    return (STAFResult::kOk, kVersion);
}

sub handleHelp
{
    return (STAFResult::kOk,
          "BEAKERLIB Service Help" . $fLineSep. 
           $fLineSep . "LIST" . $fLineSep . 
           "VERSION" . $fLineSep . "HELP");

}


#Termination/Destruction Phase
sub DESTROY
{
    my ($self) = @_;

    #$fLogHandle->log("DEBUG", "destroy");
    # Ask all the threads to stop, and join them.
    for my $thr (@{ $self->{threads_list} })
    {
        $work_queue->enqueue('stop');
    }

    # perform any cleanup for the service here

    #unregisterHelpData(kBEAKERLIBInvalidNumber);

    #Un-register the service handle
    $fHandle->unRegister();
}


###############################################################################
#                           Local service function
###############################################################################
sub print_dump
{
    my ($logfd, $data_name, $data_ref) = @_;

    # config data dumper
    $Data::Dumper::Terse = 0;
    my $dump_name = '*' . "$data_name";
    my $dump_data = Data::Dumper->Dump([$data_ref], [$dump_name]);

    $logfd->log("DEBUG", $dump_data);
    
    return;
}

###############################################################################
1;  # require expects this module to return true (!0)
###############################################################################
