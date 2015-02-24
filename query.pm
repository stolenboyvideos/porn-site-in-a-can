
package query;

use strict;
use warnings;

use Carp 'confess';

use config;

use DBI;

my $dbname;  
my $dbuser;  
my $dbpass;  
my $dbh; 

BEGIN {
    $dbname = $config::dbname; 
    $dbuser = $config::dbuser; 
    $dbpass = $config::dbpass; 
    $dbh = DBI->connect( "DBI:mysql:database=$dbname", $dbuser, $dbpass) or die DBI->errstr; 
};

sub import {
    my $package = $_[0];

    no strict 'refs';
    *{caller() . '::query'} = sub {
        my $sql = shift or confess "no sql";
        my $cb = pop if @_ and ref($_[-1]) eq 'CODE';
        my @args = @_;

        $dbh or die;

        my $sth = $dbh->prepare($sql) or confess $dbh->errstr;

        $sth->execute(@args) or confess $sth->errstr;

        if( $sql =~ m{^ *insert} ) {

            return $dbh->{mysql_insertid};

        } elsif( $sql =~ m{^ *select} ) {

            my @results;

            while(my $row = $sth->fetchrow_hashref) {
                push @results, $cb ? $cb->(bless $row, 'query::rec') : bless $row, 'query::rec';
            }

            return wantarray ? @results : bless \@results, 'query::set';

        } else {

            return $dbh; # maybe they can fish whatever they need out of there
            
        }

    };
}

#

package query::rec;
    
sub AUTOLOAD :lvalue {
    my $self = shift;
    my $method = our $AUTOLOAD;
    $method =~ s/.*:://;
    return if $method eq 'DESTROY'; 
    $self->{$method};
}

sub write {
    my $self = shift;
    my $table = shift or die;
    $self->{id} or die;
    my @keys = sort { $a cmp $b } grep { $_ ne 'id' } keys %$self;
    my @cols = join ', ', map "$_ = ?", @keys;
    my @vals = map $self->{$_}, @keys;
    my $sth = $dbh->prepare( "update $table set @cols where id = ?" ) or die $dbh->errstr;
    $sth->execute( @vals, $self->{id} ) or die $dbh->errstr;
    1;
}

#

package query::set;

sub num_rows {
    my $self = shift;
    return scalar @$self;
}

my %rows_cache;

sub rows {
    my $self = shift;
    # API shim for what I had been doing
    # create an array indexed by the id of each item in the array
    # with mysql auto_increment, results start at 1 but the array is indexed starting at 0; correct for that
    # also, if some items weren't returned by the query, there needs to be an appropriate gap in the array
    return $rows_cache{ $self } if $rows_cache{ $self };
    my $ret = [];
    for my $row ( @$self ) {
        $ret->[ $row->id ] = $row;
    }
    $rows_cache{ $self } = $ret;
    return $ret;
}

1;
