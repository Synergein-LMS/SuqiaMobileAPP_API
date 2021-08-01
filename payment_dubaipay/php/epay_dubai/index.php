<?php
error_reporting(-1);
ini_set('display_errors', 1);

require __DIR__ . '/vendor/autoload.php';

use RobRichards\WsePhp\WSSESoap;
use RobRichards\XMLSecLibs\XMLSecurityKey;

define('PRIVATE_KEY', __DIR__ .'/beta_suqia_ae.pem');
define('CERT_FILE', __DIR__ .'/Suqia.pem');
define('SERVICE_CERT', __DIR__ .'/epay5.dubai.ae.pem');

class MySoap extends SoapClient
{

    public function __doRequest($request, $location, $saction, $version, $one_way = NULL)
    {

        $doc = new DOMDocument('1.0');
        $doc->loadXML($request);

        $objWSSE = new WSSESoap($doc);

        /* add Timestamp with no expiration timestamp */
        $objWSSE->addTimestamp();

        /* create new XMLSec Key using AES256_CBC and type is private key */
        $objKey = new XMLSecurityKey(XMLSecurityKey::RSA_SHA1, array('type' => 'private'));

        /* load the private key from file - last arg is bool if key in file (true) or is string (false) */
        $objKey->loadKey(PRIVATE_KEY, true);

        /* Sign the message - also signs appropiate WS-Security items */
        $options = array("insertBefore" => false);
        $objWSSE->signSoapDoc($objKey, $options);

        /* Add certificate (BinarySecurityToken) to the message */
        $token = $objWSSE->addBinaryToken(file_get_contents(CERT_FILE));

        /* Attach pointer to Signature */
        $objWSSE->attachTokentoSig($token);

        $objKey = new XMLSecurityKey(XMLSecurityKey::AES256_CBC);
        $objKey->generateSessionKey();

        $siteKey = new XMLSecurityKey(XMLSecurityKey::RSA_OAEP_MGF1P, array('type' => 'public'));
        $siteKey->loadKey(SERVICE_CERT, true, true);

        $options = array("KeyInfo" => array("X509SubjectKeyIdentifier" => true));
        $objWSSE->encryptSoapDoc($siteKey, $objKey, $options);

        $retVal = parent::__doRequest($objWSSE->saveXML(), $location, $saction, $version);

        $doc = new DOMDocument();
        $doc->loadXML($retVal);

        $options = array("keys" => array("private" => array("key" => PRIVATE_KEY, "isFile" => true, "isCert" => false,'passphrase'=>'Change1$$')));
        $objWSSE->decryptSoapDoc($doc, $options);
	return $doc->saveXML();
        
    }

	public function getCurrentTimestamp(){
		$tz = 'Asia/Dubai'; // your required location time zone.
		$timestamp = time() - 5*60;
		$dt = new DateTime("now", new DateTimeZone($tz)); //first argument "must" be a string
		$dt->setTimestamp($timestamp); //adjust the object to correct timestamp
		$date = $dt->format('Y-m-d');
		$time = $dt->format('H:i:s+m:s');
		$time_stamp = $date."T".$time."";
		$time_last = $dt->format('H:i:s');
		$data = array('date'=>$date, 'time'=>$time_last);
		return $data;
	}
}

$json_req = json_decode($argv[1], true);

$wsdl = 'https://epayment.dubai.ae/ePayHub/WSDL/PaymentAPIService.wsdl';
//$wsdl = $json_req['wsdl'];
//$sc = new MySoap($wsdl);
$sc = new MySoap($wsdl, array('proxy_host' => "100.127.10.108", 'proxy_port' => "8080"));

try {

$time_stamp 		= $sc->getCurrentTimestamp();
$date 				= $time_stamp['date'];
$time 				= $time_stamp['time'];
$time_stamp_final 	= $date."T".$time."+04:00";
//$sp_tranaction_id 	= $sc->getUniqueTansactionId();

// web service input params
$request_param = array(
	'transactionInfo' => array(
    		"spCode" => $json_req['spCode'],
    		"servCode" => $json_req['servCode'],
    		"sptrn" => $json_req['sptrn'],
   		 "amount"=>array( '_' => $json_req['amount'], 'currency'=> $json_req['currency']),
		"timestamp" => $time_stamp_final,
		"description" => $json_req['description'],
		"type" => $json_req['type'],
		"versionCode" => $json_req['versionCode'],
		"paymentChannel" => $json_req['paymentChannel']
         ),
	"userInfo" => array(
		"isAuthenticated" => $json_req['isAuthenticated'],
		"userId" => $json_req['userId'],
		"userName" => $json_req['userName'],
		"fullNameEn" => $json_req['fullNameEn'],
		"fullNameAr" => "null",
		"poBox" => "null",
		"mobileNo" => $json_req['mobileNo'],
		"email" => $json_req['email'],
		
	),
	"serviceInfos" => array (
		"service" => array (
			"serviceNameEn" => $json_req['serviceNameEn'],
			"serviceNameAr" => "null ",
			"serviceId" => $json_req['serviceId'],
			"gessServiceId" => "null",
			"beneficiaryInfos" => array (
				"beneficiaryInfo" => array (
					 "accountId" => $json_req['accountId'],
					 "txnAmount" => array('_' => $json_req['amount'], 'currency'=> $json_req['currency']),
					 "fullNameEn" =>$json_req['fullNameEn'],
					 "fullNameAr" => "null",
					 "mobileNo" => $json_req['mobileNo'],
					 "email" => $json_req['email'],
					
					 "type" =>  $json_req['partner_type'],
					 "companyInfo" => array (
						 "companyNameEn" => $json_req['companyNameEn'],
					 ),
					 "additionalParams" => array (
						 "entry" => array (
						 "key" => "",
						 "value" => ""
						  )
					   )
			           )
			  ),
			 "additionalParams" => array (
				 "entry" => array (
					 "key" => "",
					 "value" => ""
				 )
			 )
	         )
	)
	
	     
);


$out = $sc->generateTransactionToken($request_param);
	//if($out->valid==1){
		//$redirect_url = $out->uri;
		//header("Location:".$redirect_url);
		//exit;
	//}
	print_r(json_encode($out)); 
} catch (SoapFault $fault) {
	echo "<pre>";
        var_dump($fault);

}

