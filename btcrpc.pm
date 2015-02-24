
package btcrpc;

use strict;
use warnings;

use lib '/home1/stolezzx/lib';

# TODO should take the txid of the payment to 16WTN for validation, and not allow the same txid to be used twice, and compute the pay-out from that record
# TODO would it have made more sense to just do this one command instead?  sendfrom "fromaccount" "tobitcoinaddress" amount ( minconf "comment" "comment-to" )

use JSON::RPC::Client;
use Data::Dumper;
use LWP;
use LWP::UserAgent;
use JSON::PP;

use config;

my $fee = 0.0001;
my $address = $config::address;
my $uri = 'http://127.0.0.1:8332/';

my $client = JSON::RPC::Client->new;

sub warn { print "$_[0]<br>\n" } # XXX

sub send {

    my $to = shift or die;
    my $amount = shift or die;

    $client->ua->credentials(
       "127.0.0.1:8332", 'jsonrpc', 'bitcoinrpc' => $config::bitcoincorerpcpass,
    );

    my ($tx_hash, $tx_output_n, $output_value, $output_script) = listunspent($amount);

    my $raw_tx = createrawtransaction( $tx_hash, $tx_output_n, $output_value, $output_script, $to, $amount );
    
    $raw_tx = signrawtransaction($raw_tx);
    
    my $txid = sendrawtransaction($raw_tx);

    warn "sent with TXID $txid";

    return $txid;

}

#
#
#

sub cmd {

    my $cmd = shift;

    #my $cmd = {
    #    method  => 'getinfo',
    #    params  => [],
    # };

    my $res = $client->call( $uri, $cmd );
 
    if ($res){
        if ($res->is_error) { die "Error : ", $res->error_message; }
        else { 
            print Dumper($res->result);  # debug
            return $res->result;
        }
    } else {
        die $client->status_line;
    }
}


# https://bitcoin.org/en/developer-examples#simple-spending

sub listunspent {
    # https://bitcoin.org/en/developer-reference#listunspent
    my $amount_to_spend = shift;
    my $cmd = {
        method  => 'listunspent',
        params  => [0],    # no confirmations needed
    };
    my $outputs = cmd($cmd);
    for my $output ( @$outputs ) {
        if( $output->{amount} >= $amount_to_spend ) {
            return ($output->{txid}, $output->{vout}, $output->{amount}, $output->{scriptPubKey});
        }
    }
    die "no unspent output big enough or maybe at all";

}

sub createrawtransaction {
    # https://bitcoin.org/en/developer-reference#createrawtransaction
    my ( $tx_hash, $tx_output_n, $output_value, $output_script, $to_address, $send_value) = @_;

    # values are floats.  this is bad.

    my $change = $output_value - $send_value - $fee;
    warn "output value $output_value - send value $send_value - fee $fee";
    $change = 0 if $change < 1e-10; # ffs, why are we using floats
    die "not enough money in that output" if $change < 0;

    my $cmd = {
        method  => 'createrawtransaction',
        params  => [
            [ 
                # inputs
                {
                    txid  => $tx_hash,
                    vout  => $tx_output_n,
                },
            ],
            { 
                # outputs
                $to_address   => 0+$send_value,
                $address      => 0+$change,
            },
        ],
    };

    if( $change == 0 ) {
        delete ${ $cmd->{params}->[1] }{$address};  # remove the change output if there is no change; unlikely that we'll exactly use an output but there it is
    }

    # warn "sending: " . Dumper $cmd;  # huh.  Dumper causes the string rep to be cached, and JSON picks up on this...?  nope, coin values are still getting quoted
    warn "sending: " . encode_json($cmd);

    my $tx = cmd($cmd);

    warn Dumper $tx;  # looks like:
    # $VAR1 = '0100000001b37251be9dfbb03de8acfcc02f10cf3feb758e7081c4847f71f0ca4a92235a490100000000ffffffff0170f30500000000001976a914e4cedd649068a5595c59cc0f847eafb179df284288ac00000000';

    return $tx;

}

# signrawtransaction "hexstring" ( [{"txid":"id","vout":n,"scriptPubKey":"hex","redeemScript":"hex"},...] ["privatekey1",...] sighashtype )
# Sign inputs for raw transaction (serialized, hex-encoded).
# The second optional argument (may be null) is an array of previous transaction outputs that
# this transaction depends on but may not yet be in the block chain.
# The third optional argument (may be null) is an array of base58-encoded private
# keys that, if given, will be the only keys used to sign the transaction.

sub signrawtransaction {
    my $tx = shift;

    my $cmd = {
        method  => 'signrawtransaction',
        params  => [ $tx, ],
    };

    warn "sending: " . encode_json($cmd);

    my $signed_tx = cmd($cmd);

    warn "signed tx: " . Dumper $signed_tx;  # what does this look like?
    die unless $signed_tx->{complete};
    return $signed_tx->{hex};
}

# sendrawtransaction "hexstring" ( allowhighfees )
# Submits raw transaction (serialized, hex-encoded) to local node and network.
# Also see createrawtransaction and signrawtransaction calls.
# Arguments:
# 1. "hexstring"    (string, required) The hex string of the raw transaction)
# 2. allowhighfees    (boolean, optional, default=false) Allow high fees
# Result:
# "hex"             (string) The transaction hash in hex

sub sendrawtransaction {
    my $tx = shift;

    my $cmd = {
        method  => 'sendrawtransaction',
        params  => [ $tx, ],
    };

    warn "sending: " . encode_json($cmd);

    my $txid = cmd($cmd);

    warn Dumper $txid;  # what does this look like? 
    # $VAR1 = '36c397b1e3137c57c6fe0e314d337d0642893866428451244929d51d1d9e9172';

    return $txid;
}

