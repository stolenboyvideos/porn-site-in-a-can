#!/usr/bin/perl

# request a one-time-use payment address from blockchain.info
# handle notification from blockchain.info that payment was made to that address and add value to a users account

# TODO would be better if we could COMET long poll on payment to that address, returning success when it happens or fail/retry after a timeout period, rather than polling

use strict;
use warnings;

use CGI;
use CGI::Carp 'fatalsToBrowser';

use MD5;
use JSON::PP;
use Data::Dumper;
use LWP;
use LWP::UserAgent;
use IO::Handle;

use lib '..';
use template;
use query;
use config;

my $action = CGI::param('action') || 'view';

sub hash1 { hash( $_[0], $config::hash1); }
sub hash2 { hash( $_[0], $config::hash2); }

sub hash {
    my $user_id = shift;
    my $secret = shift;
    my $md5 = MD5->new;
    $md5->reset();
    $md5->add( $user_id . $secret);
    return $md5->hexdigest();
}

if( $action eq 'payment' ) {

    # process a payment notification callback from blockchain.info

    # from https://blockchain.info/api/api_receive:

    # value The value of the payment received in satoshi. Divide by 100000000 to get the value in BTC.
    # input_address The bitcoin address that received the transaction.
    # confirmations The number of confirmations of this transaction.
    # {Custom Parameters} Any parameters included in the callback URL will be passed back to the callback URL in the notification.
    # transaction_hash The transaction hash.
    # input_transaction_hash The original paying in hash before forwarding.
    # destination_address The destination bitcoin address. Check this matches your address.

    my $user_id = CGI::param('user_id');
    my $hash = CGI::param('hash');

    my ($user) = query("select * from users where id = ?", $user_id);

    exit if ! $user; # not just forged but completely bunk; TODO log this somewhere

    if( hash1( $user_id ) ne $hash ) {
        $user->debug = "hash wrong on callback from blockchain.info";
        $user->write('users');
        exit;
    }

    my $btc = CGI::param('value') / 100_000_000;  # in satoshis; convert to BTC; right now, 0.0005, the smallest supported transaction, is about 15 cents.
    my $usd = $btc * 300;  # approximately convert from BTC to USD
    my $bytes_purchased = $usd * 1 * 1024 * 1024 * 1024;   # one gigabyte per dollar

    $user->bytes_purchased += $bytes_purchased;
    $user->debug = "purchased $btc BTC worth of data";
    $user->payment_status = "Got payment"; 
    $user->write;

    # generate some output so the proxy doesn't get impatiant and time out right away

    STDOUT->autoflush(1);
    print "Content-type: text/plain\r\n\r\n";

    if($user->referer) {
        # if the user has a referer (address) marked, pay out half of the take to that
        my $tx = CGI::param('transaction_hash'); 
        my $address = $user->referer;
        my $amount = $btc / 2;
        my $hash = hash2("$address-$amount");
        my $res;
        eval {
            my $ua = LWP::UserAgent->new();
            my $req = HTTP::Request->new( GET => "http://$config::fullnodeip/btc.cgi?txid=$tx&address=$address&amount=$amount&hash=$hash" );
            $res = $ua->request($req);
        };
        if( $@ ) {
            $user->payment_status = "Got payment; referal fee on $btc btc from txid $tx failed: eval error " . $@; 
        } elsif( $res and $res->is_error ) {
            $user->payment_status = "Got payment; referal fee on $btc btc from txid $tx failed: HTTP code " . $res->code; 
        } elsif( $res and $res->content =~ m/Software error/ ) {
            #  <h1>Software error:</h1>
            # <pre>no unspent output big enough or maybe at all at /home/user//btcrpc.pm line 92.
            # </pre>
            ( my $error ) = $res->content =~ m{<pre>.*?</pre>}sg;
            $error ||= $res->content;
            $user->payment_status = "Got payment; referal fee on $btc btc from txid $tx failed: error message " . $error;
        } elsif( $res ) {
            ( my $success ) = $res->content =~ m{<tx>.*?</tx>}sg;
            $success ||= $res->content;
            $user->payment_status = "Got payment; referal fee on $btc btc on txid $tx paid: tx " . $success;
        } else {
            $user->payment_status = "Got payment; referal fee on $btc btc on txid $tx paid: status unknown";
        }
        $user->write;
        if( $res and $res->content ) {
            open my $fh, '>>', $config::home . '/debug.log';
            print $fh $res->content;
            close $fh;
        }
    }
    
    # record this purchase in the purchases table as well

    eval {
        query( "insert into purchases (user_id, bytes_purchased, btc) values (?, ?, ?)", $user_id, $bytes_purchased, $btc, );
    };

    print "*ok*\n";

} elsif( $action eq 'check') {

    my $user = user() or die "no user";

    print "Content-type: application/json\r\n\r\n";

    if( $user->payment_status =~ m/Got payment/ ) {
        print encode_json { paid => 1, };
    } else {
        print encode_json { paid => 0, };
    }

} else {

    # request a one time use bitcoin address from blockchain.info for this user to send payment to

    print "Content-type: application/json\r\n\r\n";

    my $user = user() or die "no user";

    my $error = sub {
        my $message = shift;
        print encode_json { error => $message, };
        $user->debug = $message;
        $user->write;
        exit;
    };

    $user->cookie or $error->("Error:  you can only add value to your account if you have an account and are logged in.\n");

    # hash stuff to avoid spoofed requests

    my $user_id = $user->id;
    my $hash = hash1($user_id);

    # make a request to blockchain.info to create a payment address and request callback when funds arrive there

    my $ua = LWP::UserAgent->new();

    my $callback_url = "$config::url/payment.cgi?action=payment&user_id=$user_id&hash=$hash";

    my $req = HTTP::Request->new( GET => 'http://blockchain.info/api/receive?method=create&address=$config::address&callback=' . CGI::escape($callback_url) );

    my $res = $ua->request($req);

    $res->is_error and $error->("Payment request error: " . $res->decoded_content);

    # print "response as_string: " . $res->as_string;
    # print "response: " . $res->decoded_content;
    # response looks like:  {"input_address":"11VHvSHS9fnMPYSzzi72zkyqtaPWvG7mf","destination":"16WTNrktpQqTmxoqQMDccwp5RSmbhM2zub","fee_percent":0}

    my $payment_info = decode_json( $res->decoded_content ) or $error->("Error: no JSON data back from blockchain.info");

    $payment_info->{input_address} or $error->("Error: no input_address field back from blockchain.info");

    # re-use the same JSON message we got back from blockchain.info and return that to the webapp

    print $res->decoded_content;

    $user->payment_status = "Waiting for payment to " . $payment_info->{input_address} . " callback url " . $callback_url; 
    $user->write;

}
